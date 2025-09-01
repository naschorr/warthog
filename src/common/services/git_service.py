import logging

from git.refs.tag import TagReference

logger = logging.getLogger(__name__)

from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from git import Repo


class GitService:

    @staticmethod
    def clone_repository(destination: Path, repository_url: str) -> Path:
        """
        Clones the datamine repository to the specified destination.
        """
        logger.info(f"Cloning repository from {repository_url} to {destination}")
        repository = Repo.clone_from(repository_url, destination)

        return Path(repository.working_dir)

    @staticmethod
    def clone_repository_partial(destination: Path, repository_url: str, *, sparse_paths: list[Path]) -> Path:
        """
        Clones the datamine repository to the specified destination, using sparse checkout to only fetch specific paths.
        """
        logger.info(
            f"Cloning repository from {repository_url} to {destination} with sparse checkout for paths: {sparse_paths}"
        )

        # Clone the repository with no checkout and blob filtering
        Repo.clone_from(repository_url, destination, no_checkout=True, multi_options=["--filter=blob:none"])

        repository = Repo(destination)

        # Initialize sparse checkout
        repository.git.sparse_checkout("init", "--cone")

        # Set the sparse paths
        sparse_paths_str = [str(path) for path in sparse_paths]
        repository.git.sparse_checkout("set", *sparse_paths_str)

        # Checkout the files
        repository.git.checkout()

        return Path(repository.working_dir)

    @staticmethod
    def checkout_branch(repository_path: Path, branch: str):
        """
        Checks out the specified branch in the cloned repository.
        """
        logger.info(f"Checking out branch {branch}")

        repository = Repo(repository_path)
        repository.git.checkout(branch)

    @staticmethod
    def get_head_date(repository_path: Path, *, utc: bool = False) -> datetime:
        """
        Gets the date of the HEAD commit in the repository.
        """
        repository = Repo(repository_path)
        head_commit = repository.head.commit
        if utc:
            return head_commit.committed_datetime.astimezone(timezone.utc).replace(tzinfo=None)
        return head_commit.committed_datetime

    @staticmethod
    def get_tags(repository_path: Path) -> list[TagReference]:
        """
        Get all tags in the repository.
        """
        repository = Repo(repository_path)
        return repository.tags

    @staticmethod
    def get_tags_between_datetimes(
        repository_path: Path, *, start: Optional[datetime] = None, end: Optional[datetime] = None
    ) -> list[TagReference]:
        """
        Get all tags in the repository between the specified start and end datetimes.
        """
        start = start or datetime.min.replace(tzinfo=timezone.utc)
        end = end or datetime.max.replace(tzinfo=timezone.utc)

        if start == end:
            raise ValueError("Start and end datetimes cannot be the same")
        if end < start:
            logger.debug("End datetime is before start datetime, swapping values")
            start, end = end, start

        tags = GitService.get_tags(repository_path)
        tags_in_range = [
            tag
            for tag in tags
            if start <= tag.commit.committed_datetime.astimezone(timezone.utc).replace(tzinfo=None) <= end
        ]
        return tags_in_range
