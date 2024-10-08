import { useEffect, useState } from 'react';
import { useDispatch } from 'react-redux';
import { useTypedSelector } from '@Store/hooks';
import {
  ProjectCard,
  ProjectsHeader,
  ProjectsMapSection,
} from '@Components/Projects';
import { useGetProjectsListQuery } from '@Api/projects';
import ProjectCardSkeleton from '@Components/Projects/ProjectCardSkeleton';
import hasErrorBoundary from '@Utils/hasErrorBoundary';
import { setCreateProjectState } from '@Store/actions/createproject';
import Pagination from '@Components/Projects/Pagination';
import Skeleton from '@Components/RadixComponents/Skeleton';
import { setCommonState } from '@Store/actions/common';

const Projects = () => {
  const dispatch = useDispatch();
  const showMap = useTypedSelector(state => state.common.showMap);
  const projectsFilterByOwner = useTypedSelector(
    state => state.createproject.ProjectsFilterByOwner,
  );
  const projectSearchKey = useTypedSelector(
    state => state.common.projectSearchKey,
  );
  const [paginationState, setSetPaginationState] = useState({
    activePage: 1,
    selectedNumberOfRows: 10,
  });

  const handlePaginationState = (value: Record<string, number>) => {
    setSetPaginationState(prev => ({ ...prev, ...value }));
  };

  // fetch api for projectsList
  const { data: projectListData, isFetching: isLoading }: Record<string, any> =
    useGetProjectsListQuery({
      queryKey: {
        // @ts-ignore
        filter_by_owner: projectsFilterByOwner === 'yes',
        page: paginationState?.activePage,
        results_per_page: paginationState?.selectedNumberOfRows,
        search: projectSearchKey,
      },
    });

  useEffect(() => {
    handlePaginationState({ activePage: 1 });
  }, [projectSearchKey, projectsFilterByOwner]);

  useEffect(() => {
    return () => {
      dispatch(setCreateProjectState({ ProjectsFilterByOwner: 'no' }));
      dispatch(setCommonState({ projectSearchKey: '' }));
    };
  }, [dispatch]);

  return (
    <section className="naxatw-px-3 naxatw-pt-2 lg:naxatw-px-16">
      <ProjectsHeader />
      <div className="naxatw-grid naxatw-gap-2 naxatw-pb-10 md:naxatw-flex md:naxatw-h-[calc(100vh-11rem)] md:naxatw-pb-0">
        <div
          className={`scrollbar naxatw-grid naxatw-grid-rows-[19rem] naxatw-gap-3 naxatw-overflow-y-auto naxatw-py-2 ${showMap ? 'naxatw-w-full naxatw-grid-cols-1 md:naxatw-w-1/3 md:naxatw-grid-cols-1 lg:naxatw-grid-cols-1 xl:naxatw-grid-cols-2' : 'naxatw-w-full naxatw-grid-cols-1 sm:naxatw-grid-cols-2 md:naxatw-grid-cols-3 lg:naxatw-grid-cols-5'}`}
          style={{ gridAutoRows: '19rem' }}
        >
          {isLoading ? (
            <>
              {Array.from({ length: 6 }, (_, index) => (
                <ProjectCardSkeleton key={index} />
              ))}
            </>
          ) : (
            <>
              {!projectListData?.results?.length && (
                <div>No projects available</div>
              )}
              {(projectListData?.results as Record<string, any>[])?.map(
                (project: Record<string, any>) => (
                  <ProjectCard
                    key={project.id}
                    id={project.id}
                    slug={project.slug}
                    imageUrl={project?.image_url}
                    title={project.name}
                    description={project.description}
                    totalTasks={project?.total_task_count}
                    status={project?.status}
                    completedTask={project?.completed_task_count}
                  />
                ),
              )}
            </>
          )}
        </div>
        {showMap && (
          <div className="naxatw-h-[70vh] naxatw-w-full naxatw-py-2 naxatw-shadow-xl md:naxatw-h-full md:naxatw-w-2/3">
            {!isLoading ? (
              <ProjectsMapSection projectList={projectListData?.results} />
            ) : (
              <Skeleton className="axatw-animate-pulse naxatw-h-full naxatw-w-full" />
            )}
          </div>
        )}
      </div>
      <div className="naxatw-px-3 lg:naxatw-px-16">
        <Pagination
          totalCount={projectListData?.pagination?.total}
          currentPage={paginationState?.activePage}
          pageSize={paginationState?.selectedNumberOfRows}
          handlePaginationState={handlePaginationState}
        />
      </div>
    </section>
  );
};

export default hasErrorBoundary(Projects);
