"""
Learning Paths Compatible Search Engine

This engine acts as a proxy to MeiliSearch, allowing additional data processing
for learning paths content while maintaining compatibility with the existing search interface.

Usage:
    SEARCH_ENGINE = "learning_paths.search_engine.LearningPathsCompatibleSearchEngine"
"""

import logging
from copy import deepcopy

from crum import get_current_request

from search.search_engine_base import SearchEngine
from search.meilisearch import MeilisearchEngine

logger = logging.getLogger(__name__)


class LearningPathsCompatibleSearchEngine(SearchEngine):
    """
    Learning Paths compatible search engine that wraps MeiliSearch.

    Adds learning path specific data processing while delegating core
    search functionality to the MeiliSearch engine.
    """

    def __init__(self, index=None):
        super().__init__(index=index)
        self._meilisearch_engine = MeilisearchEngine(index=index)

    def index(self, sources, **kwargs):
        """Index documents with learning paths enhancements."""
        logger.info(
            "LearningPathsCompatibleSearchEngine.index: Processing %d documents for index %s",
            len(sources),
            self.index_name
        )

        # Enhance documents with learning paths data
        enhanced_sources = self._enhance_documents(sources)

        # Delegate to MeiliSearch
        self._meilisearch_engine.index(enhanced_sources, **kwargs)

    def search(
        self,
        query_string=None,
        field_dictionary=None,
        filter_dictionary=None,
        exclude_dictionary=None,
        aggregation_terms=None,
        log_search_params=False,
        **kwargs,
    ):
        """Search with learning paths result enhancements."""
        logger.info(
            "LearningPathsCompatibleSearchEngine.search: Executing search for query '%s' on index %s",
            query_string,
            self.index_name
        )

        # Delegate to MeiliSearch
        results = self._meilisearch_engine.search(
            query_string=query_string,
            field_dictionary=field_dictionary,
            filter_dictionary=filter_dictionary,
            exclude_dictionary=exclude_dictionary,
            aggregation_terms=aggregation_terms,
            log_search_params=log_search_params,
            **kwargs
        )

        # Enhance results with learning paths data
        enhanced_results = self._enhance_results(results, query_string)

        return enhanced_results

    def remove(self, doc_ids, **kwargs):
        """Remove documents with learning paths cleanup."""
        logger.info(
            "LearningPathsCompatibleSearchEngine.remove: Removing %d documents from index %s",
            len(doc_ids),
            self.index_name
        )

        # Delegate to MeiliSearch
        self._meilisearch_engine.remove(doc_ids, **kwargs)

    def _enhance_documents(self, sources):
        """Add learning paths specific data to documents before indexing."""
        enhanced_sources = []

        for source in sources:
            enhanced_doc = deepcopy(source)

            # Add learning paths metadata
            enhanced_doc['learning_paths_indexed_at'] = self._get_current_timestamp()

            # Check if document is learning path related
            if self._is_learning_path_content(enhanced_doc):
                enhanced_doc['content_type'] = 'learning_path'
                enhanced_doc['learning_path_enhanced'] = True

                # Add learning path specific fields
                if 'content' in enhanced_doc:
                    content = enhanced_doc['content']
                    if 'display_name' in content:
                        enhanced_doc['display_name_searchable'] = content['display_name'].lower()

                    # Add path step information if available
                    if 'step_order' in enhanced_doc:
                        enhanced_doc['is_path_step'] = True
                        enhanced_doc['step_category'] = self._categorize_step(enhanced_doc.get('step_order', 0))

            enhanced_sources.append(enhanced_doc)

        logger.info("Enhanced %d documents with learning paths data", len(enhanced_sources))
        return enhanced_sources

    def _enhance_results(self, results, query_string):
        """Add learning paths as search results to maintain UI compatibility."""
        enhanced_results = deepcopy(results)

        # Get matching learning paths and convert them to search result format
        learning_path_results = self._get_learning_paths_as_search_results(query_string)

        if learning_path_results:
            # Add learning paths to existing results
            enhanced_results['results'].extend(learning_path_results)
            enhanced_results['total'] += len(learning_path_results)

            # Update max_score if learning paths have higher scores
            for lp_result in learning_path_results:
                if lp_result.get('score', 0) > enhanced_results.get('max_score', 0):
                    enhanced_results['max_score'] = lp_result['score']

        logger.info("Enhanced search results with %d learning paths", len(learning_path_results))
        return enhanced_results

    def _is_learning_path_content(self, doc):
        """Check if document is related to learning paths."""
        # Check for learning path indicators
        content = doc.get('content', {})
        doc_id = doc.get('id', '')

        return (
            'learning_path' in doc_id.lower() or
            'path' in content.get('display_name', '').lower() or
            'step_order' in doc or
            'learning_path_id' in doc
        )

    def _categorize_step(self, step_order):
        """Categorize learning path steps."""
        if step_order <= 2:
            return 'introductory'
        elif step_order <= 5:
            return 'intermediate'
        else:
            return 'advanced'

    def _get_learning_paths_as_search_results(self, query_string):
        """Convert learning paths to search result format for UI compatibility."""

        try:
            from learning_paths.models import LearningPath

            # Get learning paths visible to user and filter by query
            current_request = get_current_request()
            learning_paths = LearningPath.objects.get_paths_visible_to_user(current_request.user)

            # Apply text search filter if query exists
            if query_string:
                learning_paths = learning_paths.filter(
                    display_name__icontains=query_string
                ) | learning_paths.filter(
                    description__icontains=query_string
                ) | learning_paths.filter(
                    subtitle__icontains=query_string
                )
                logger.info("Found %d learning paths matching query '%s'", learning_paths.count(), query_string)
            else:
                logger.info("Found %d learning paths visible to user (no query filter)", learning_paths.count())

            search_results = []
            for lp in learning_paths:
                # Convert learning path to search result format
                search_result = {
                    '_id': f'learning_path:{lp.key}',
                    '_index': self.index_name,
                    '_type': 'learning_path',
                    'score': self._calculate_learning_path_score(lp, query_string),
                    'data': {
                        'id': f'learning_path:{lp.key}',
                        'course': f'learning_path:{lp.key}',  # Add course field like other results
                        'content': {
                            'display_name': lp.display_name,
                            'overview': lp.description or '',
                            'subtitle': lp.subtitle or '',
                            'language': 'en',  # Default language
                            'start_date': lp.created.isoformat() if lp.created else None,
                            'number': lp.key.run,
                            'short_description': lp.subtitle or lp.description or '',  # Add short description
                        },
                        'org': lp.key.org,
                        'content_type': 'learning_path',
                        'learning_path_key': str(lp.key),
                        'learning_path_steps_count': lp.steps.count() if hasattr(lp, 'steps') else 0,
                        'image_url': self._get_learning_path_image_url(lp),
                        'start': lp.created.isoformat() if lp.created else None,  # Add start field like courses
                        'number': lp.key.run,
                        'modes': ['learning_path'],  # Add modes field
                        'language': 'en',  # Add language field at top level
                        'catalog_visibility': 'both',  # Add catalog visibility
                        'level': lp.level if hasattr(lp, 'level') and lp.level else 'beginner',
                        'duration_in_days': lp.duration_in_days if hasattr(lp, 'duration_in_days') and lp.duration_in_days else None,
                        'sequential': lp.sequential if hasattr(lp, 'sequential') else False,
                    }
                }
                search_results.append(search_result)

            return search_results

        except ImportError:
            logger.warning("LearningPath model not available")
            return []
        except Exception as e:
            logger.error("Error fetching learning paths: %s", e, exc_info=True)
            return []

    def _calculate_learning_path_score(self, learning_path, query_lower):
        """Calculate relevance score for learning path based on query match."""
        # Nothing at the moment
        return 1.0

    def _get_learning_path_image_url(self, learning_path):
        """Get the proper image URL for a learning path."""
        try:
            if hasattr(learning_path, 'image') and learning_path.image:
                # If it's a Django FileField/ImageField, get the URL
                if hasattr(learning_path.image, 'url'):
                    return learning_path.image.url
                # If it's just a string path, return as-is
                return str(learning_path.image)
            return None
        except Exception as e:
            logger.warning("Error getting image URL for learning path %s: %s", learning_path.key, e)
            return None

    @property
    def underlying_engine(self):
        """Access to the underlying MeiliSearch engine."""
        return self._meilisearch_engine

    def _get_current_timestamp(self):
        """Get current timestamp as ISO string."""
        from datetime import datetime
        return datetime.now().isoformat()