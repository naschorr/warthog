import logging

logger = logging.getLogger(__name__)

import tempfile
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from git import Repo
from git.cmd import Git
from git.refs.tag import TagReference


class GitRepositoryClient:

    # Lifecycle

    def __init__(self, repository_url: str, repository_dir_path: Path):
        """
        Initializes the GitRepositoryClient.

        Args:
            repository_url (str): The URL of the Git repository to clone.
            repository_dir_path (Path): The local directory path where the repository will be cloned.
        """
        self._repository_url = repository_url
        self._repository_dir_path = repository_dir_path

        self._git_client = Git()
        self._repository: Optional[Repo] = None
        self._is_cloned = False

    # Properties

    @property
    def repository_url(self) -> str:
        """
        Get the URL of the remote repository.
        """
        return self._repository_url

    @property
    def repository_dir_path(self) -> Path:
        """
        Get the local directory path where the repository is cloned.
        """
        return self._repository_dir_path

    @property
    def repository(self) -> Repo:
        """
        Get the local repository. Raises ValueError if not cloned yet.
        """
        if not self._is_cloned or self._repository is None:
            raise ValueError("Repository has not been cloned yet. Call clone() or clone_partial() first.")
        return self._repository

    @property
    def is_cloned(self) -> bool:
        """
        Check if the repository has been cloned locally.
        """
        return self._is_cloned

    # Methods

    # Remote Operations (no cloning required)

    def query_remote_tags(self) -> dict[str, str]:
        """
        Query remote repository for available tags without cloning.

        Returns:
            dict[str, str]: Dictionary mapping tag names to their commit SHAs
        """
        try:
            logger.debug(f"Querying remote tags from {self._repository_url}")

            # Get all remote references
            remote_refs_output = self._git_client.ls_remote(self._repository_url, tags=True)

            tags = {}
            for line in remote_refs_output.split("\n"):
                if line.strip():
                    sha, ref = line.split("\t", 1)

                    # Parse tag names, handling both annotated and lightweight tags
                    if ref.startswith("refs/tags/"):
                        tag_name = ref.replace("refs/tags/", "")

                        # Skip peeled refs (annotated tag objects vs commit objects)
                        if not tag_name.endswith("^{}"):
                            tags[tag_name] = sha

            logger.debug(f"Found {len(tags)} remote tags")
            return tags

        except Exception as e:
            logger.error(f"Failed to query remote tags from {self._repository_url}: {e}")
            return {}

    def query_remote_branches(self) -> dict[str, str]:
        """
        Query remote repository for available branches without cloning.

        Returns:
            dict[str, str]: Dictionary mapping branch names to their commit SHAs
        """
        try:
            logger.debug(f"Querying remote branches from {self._repository_url}")

            # Get all remote branch references
            remote_refs_output = self._git_client.ls_remote(self._repository_url, heads=True)

            branches = {}
            for line in remote_refs_output.split("\n"):
                if line.strip():
                    sha, ref = line.split("\t", 1)

                    if ref.startswith("refs/heads/"):
                        branch_name = ref.replace("refs/heads/", "")
                        branches[branch_name] = sha

            logger.debug(f"Found {len(branches)} remote branches")
            return branches

        except Exception as e:
            logger.error(f"Failed to query remote branches from {self._repository_url}: {e}")
            return {}

    # Cloning Operations

    def clone(self) -> Repo:
        """
        Clone the full repository to the local directory.

        Returns:
            Repo: The cloned repository object
        """
        if not self._repository_dir_path.exists():
            logger.debug(f"Creating destination directory {self._repository_dir_path}")
            self._repository_dir_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Cloning repository from {self._repository_url} to {self._repository_dir_path}")
        self._repository = Repo.clone_from(self._repository_url, self._repository_dir_path)
        self._is_cloned = True

        return self._repository

    def clone_partial(self, *, sparse_paths: list[Path]) -> Repo:
        """
        Clone the repository with sparse checkout to only fetch specific paths.

        Args:
            sparse_paths (list[Path]): List of paths within the repository to include in the sparse checkout.

        Returns:
            Repo: The cloned repository object
        """
        if not self._repository_dir_path.exists():
            logger.debug(f"Creating destination directory {self._repository_dir_path}")
            self._repository_dir_path.mkdir(parents=True, exist_ok=True)

        # Clone the repository with no checkout and blob filtering
        logger.info(
            f"Cloning repository from {self._repository_url} to {self._repository_dir_path} with sparse checkout for paths: {sparse_paths}"
        )
        self._repository = Repo.clone_from(
            self._repository_url, self._repository_dir_path, no_checkout=True, multi_options=["--filter=blob:none"]
        )

        # Initialize sparse checkout
        self._repository.git.sparse_checkout("init", "--cone")

        # Set the sparse paths
        sparse_paths_str = [str(path) for path in sparse_paths]
        self._repository.git.sparse_checkout("set", *sparse_paths_str)

        # Checkout the files
        self._repository.git.checkout()

        self._is_cloned = True
        return self._repository

    # Local Repository Operations (require cloning first)

    def get_tags_between_datetimes(
        self, *, start: Optional[datetime] = None, end: Optional[datetime] = None
    ) -> list[TagReference]:
        """
        Get tags between specified datetimes from the cloned repository.

        This method requires the repository to be cloned first using clone() or clone_partial().
        For best performance with large repositories, use clone_partial() first.

        Args:
            start (Optional[datetime]): The start datetime. If None, defaults to the earliest possible datetime.
            end (Optional[datetime]): The end datetime. If None, defaults to the latest possible datetime.

        Returns:
            list[TagReference]: List of TagReference objects for tags within the datetime range
        """
        if not self._is_cloned:
            raise ValueError(
                "Repository must be cloned before getting tags by date. Call clone() or clone_partial() first."
            )

        try:
            logger.debug(f"Getting tags with date filtering from cloned repository")

            start = start or datetime.min.replace(tzinfo=timezone.utc)
            end = end or datetime.max.replace(tzinfo=timezone.utc)

            if start == end:
                raise ValueError("Start and end datetimes cannot be the same")
            if end < start:
                logger.debug("End datetime is before start datetime, swapping values")
                start, end = end, start

            logger.debug(f"Filtering tags by commit dates between {start} and {end}")

            tags_in_range = []
            for tag_ref in self.repository.tags:
                try:
                    # Get the commit datetime for this tag
                    commit_datetime = tag_ref.commit.committed_datetime.astimezone(timezone.utc).replace(tzinfo=None)

                    # Check if commit is within the date range
                    if start <= commit_datetime <= end:
                        tags_in_range.append(tag_ref)
                        logger.debug(
                            f"Tag {tag_ref.name} ({tag_ref.commit.hexsha[:8]}) is within date range: {commit_datetime}"
                        )

                except Exception as e:
                    logger.debug(f"Could not get commit date for tag {tag_ref.name}: {e}")
                    continue

            logger.debug(f"Found {len(tags_in_range)} tags within date range")
            return tags_in_range

        except Exception as e:
            logger.error(f"Failed to get tags with date filtering: {e}")
            return []

    def checkout_branch(self, branch: str):
        """
        Check out the specified branch in the cloned repository.

        Args:
            branch (str): The name of the branch to check out
        """
        if not self._is_cloned:
            raise ValueError("Repository must be cloned before checking out branches. Call clone() first.")

        logger.debug(f"Checking out branch {branch}")
        self.repository.git.checkout(branch)

    def get_head_date(self, *, utc: bool = False) -> datetime:
        """
        Get the date of the HEAD commit in the repository.

        Args:
            utc (bool): Whether to return the date in UTC. Defaults to False.

        Returns:
            datetime: The date of the HEAD commit.
        """
        if not self._is_cloned:
            raise ValueError("Repository must be cloned before getting HEAD date. Call clone() first.")

        logger.debug("Getting HEAD commit date")
        head_datetime = self.repository.head.commit.committed_datetime
        if utc:
            return head_datetime.astimezone(timezone.utc).replace(tzinfo=None)
        return head_datetime

    def get_tags(self) -> list[TagReference]:
        """
        Get all tags in the local repository.

        Returns:
            list[TagReference]: List of all tags in the repository.
        """
        if not self._is_cloned:
            raise ValueError("Repository must be cloned before getting tags. Call clone() first.")

        logger.debug("Getting all tags in the repository")
        return self.repository.tags
