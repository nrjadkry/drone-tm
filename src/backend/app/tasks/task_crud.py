from psycopg import Connection
from fastapi import HTTPException
from psycopg.rows import dict_row
import uuid
from app.models.enums import HTTPStatus, State


async def update(
    db: Connection,
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    user_id: str,
    comment: str,
    initial_state: State,
    final_state: State,
):
    async with db.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
        WITH last AS (
            SELECT *
            FROM task_events
            WHERE project_id = :%(project_id)s AND task_id = :%(task_id)s
            ORDER BY created_at DESC
            LIMIT 1
        ),
        updated AS (
            UPDATE task_events
            SET state = :%(final_state)s, comment = :%(comment)s, created_at = now()
            WHERE EXISTS (
                SELECT 1
                FROM last
                WHERE user_id = :%(user_id)s AND state = :%(initial_state)s
            )
            RETURNING project_id, task_id, user_id, state
        )
        INSERT INTO task_events (event_id, project_id, task_id, user_id, state, comment, created_at)
        SELECT gen_random_uuid(), :%(project_id)s, :%(task_id)s, :%(user_id)s, :%(final_state)s, :%(comment)s, now()
        WHERE NOT EXISTS (
            SELECT 1
            FROM updated
        )
        RETURNING project_id, task_id, user_id, state;
    """,
            {
                "project_id": str(project_id),
                "task_id": str(task_id),
                "user_id": str(user_id),
                "comment": comment,
                "initial_state": initial_state.name,
                "final_state": final_state.name,
            },
        )

    result = await db.fetchone()

    return {
        "project_id": result["project_id"],
        "task_id": result["task_id"],
        "comment": comment,
    }


async def get_project_task_by_id(db: Connection, user_id: str):
    """Get a list of pending tasks created by a specific user (project creator)."""
    async with db.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """SELECT id FROM projects WHERE author_id = %(user_id)s""",
            {"user_id": user_id},
        )

        project_ids_result = await cur.fetchall()

        project_ids = [row["id"] for row in project_ids_result]
        await cur.execute(
            """
            SELECT t.id AS task_id, te.event_id, te.user_id, te.project_id, te.comment, te.state, te.created_at
            FROM tasks t
            LEFT JOIN task_events te ON t.id = te.task_id
            WHERE t.project_id = ANY(%(project_ids)s)
            AND te.state = %(state)s
            ORDER BY t.project_task_index;""",
            {"project_ids": project_ids, "state": "REQUEST_FOR_MAPPING"},
        )

        try:
            db_tasks = await cur.fetchall()
        except Exception as e:
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch project tasks. {e}",
            )
        return db_tasks


async def request_mapping(
    db: Connection,
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    user_id: str,
    comment: str,
):
    async with db.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            WITH last AS (
                SELECT *
                FROM task_events
                WHERE project_id= %(project_id)s AND task_id= %(task_id)s
                ORDER BY created_at DESC
                LIMIT 1
            ),
            released AS (
                SELECT COUNT(*) = 0 AS no_record
                FROM task_events
                WHERE project_id= %(project_id)s AND task_id= %(task_id)s AND state = %(unlocked_to_map_state)s
            )
            INSERT INTO task_events (event_id, project_id, task_id, user_id, comment, state, created_at)

            SELECT
                gen_random_uuid(),
                %(project_id)s,
                %(task_id)s,
                %(user_id)s,
                %(comment)s,
                %(request_for_map_state)s,
                now()
            FROM last
            RIGHT JOIN released ON true
            WHERE (last.state = %(unlocked_to_map_state)s OR released.no_record = true);
            """,
            {
                "project_id": str(project_id),
                "task_id": str(task_id),
                "user_id": str(user_id),
                "comment": comment,
                "unlocked_to_map_state": State.UNLOCKED_TO_MAP.name,
                "request_for_map_state": State.REQUEST_FOR_MAPPING.name,
            },
        )

        await cur.fetchone()

        return {"project_id": project_id, "task_id": task_id, "comment": comment}


async def update_or_create_task_state(
    db: Connection,
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    user_id: str,
    comment: str,
    initial_state: State,
    final_state: State,
):
    # Update or insert task event
    async with db.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            WITH last AS (
                SELECT *
                FROM task_events
                WHERE project_id = %(project_id)s AND task_id = %(task_id)s
                ORDER BY created_at DESC
                LIMIT 1
            ),
            updated AS (
                UPDATE task_events
                SET state = %(final_state)s, comment = %(comment)s, created_at = now()
                WHERE EXISTS (
                    SELECT 1
                    FROM last
                    WHERE user_id = %(user_id)s AND state = %(initial_state)s
                )
                RETURNING project_id, task_id, user_id, state
            )
            INSERT INTO task_events (event_id, project_id, task_id, user_id, state, comment, created_at)
            SELECT gen_random_uuid(), %(project_id)s, %(task_id)s, %(user_id)s, %(final_state)s, %(comment)s, now()
            WHERE NOT EXISTS (
                SELECT 1
                FROM updated
            )
            RETURNING project_id, task_id, user_id, state;
        """,
            {
                "project_id": str(project_id),
                "task_id": str(task_id),
                "user_id": str(user_id),
                "comment": comment,
                "initial_state": initial_state.name,
                "final_state": final_state.name,
            },
        )

        result = await cur.fetchone()
        return {
            "project_id": result["project_id"],
            "task_id": result["task_id"],
            "comment": comment,
        }


async def get_all_tasks_with_states(db: Connection, project_id: uuid.UUID):
    async with db.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            WITH all_tasks AS (
                SELECT id AS task_id
                FROM tasks
                WHERE project_id = %(project_id)s
            ),
            latest_task_events AS (
                SELECT DISTINCT ON (task_id) task_id, state
                FROM task_events
                WHERE project_id = %(project_id)s
                ORDER BY task_id, created_at DESC
            )
            SELECT
                %(project_id)s AS project_id,
                all_tasks.task_id,
                COALESCE(latest_task_events.state, %(default_state)s) AS state
            FROM all_tasks
            LEFT JOIN latest_task_events
            ON all_tasks.task_id = latest_task_events.task_id
            """,
            {"project_id": project_id, "default_state": State.UNLOCKED_TO_MAP.name},
        )

        tasks_with_states = await cur.fetchall()
        return tasks_with_states
