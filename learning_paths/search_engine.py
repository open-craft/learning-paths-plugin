"""
Learning Paths Compatible Search Engine

This engine acts as a proxy to MeiliSearch, allowing additional data processing
for learning paths content while maintaining compatibility with the existing search interface.

Usage:
    SEARCH_ENGINE = "learning_paths.search_engine.LearningPathsCompatibleSearchEngine"
"""

import logging
from copy import deepcopy

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
        """Add learning paths specific data to search results."""
        enhanced_results = deepcopy(results)

        # Add learning paths metadata to results
        enhanced_results['learning_paths_metadata'] = {
            'processed_by': 'LearningPathsCompatibleSearchEngine',
            'query': query_string,
            'enhancement_timestamp': self._get_current_timestamp()
        }

        # Enhance individual results
        for result in enhanced_results.get('results', []):
            data = result.get('data', {})

            # Add learning path context if this is path content
            if data.get('content_type') == 'learning_path':
                result['learning_path_context'] = {
                    'is_enhanced': True,
                    'content_type': 'learning_path'
                }

                # Boost score for learning path content
                if 'score' in result:
                    result['learning_path_boosted_score'] = result['score'] * 1.2

        logger.info("Enhanced %d search results with learning paths data", len(enhanced_results.get('results', [])))
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

    def _get_current_timestamp(self):
        """Get current timestamp as ISO string."""
        from datetime import datetime
        return datetime.now().isoformat()

    @property
    def underlying_engine(self):
        """Access to the underlying MeiliSearch engine."""
        return self._meilisearch_engine