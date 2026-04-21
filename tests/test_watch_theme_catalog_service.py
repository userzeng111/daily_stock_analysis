# -*- coding: utf-8 -*-
"""Tests for the watch theme catalog service."""

from __future__ import annotations

import unittest


class WatchThemeCatalogServiceTestCase(unittest.TestCase):
    def test_load_search_and_resolve_catalog(self) -> None:
        from src.services.watch_theme_catalog_service import WatchThemeCatalogService

        service = WatchThemeCatalogService()

        themes = service.list_themes()
        self.assertGreaterEqual(len(themes), 4)

        names = {theme.display_name for theme in themes}
        self.assertTrue({"算力", "CPO/光模块", "机器人", "半导体"}.issubset(names))

        matched = service.search_themes("光模块")
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0].display_name, "CPO/光模块")

        resolved = service.resolve_theme("算力")
        self.assertTrue(resolved.supported)
        self.assertEqual(resolved.display_name, "算力")
        self.assertGreaterEqual(len(resolved.members), 1)
        self.assertGreaterEqual(len(resolved.etfs), 1)

        unsupported = service.resolve_theme("不存在的主题")
        self.assertFalse(unsupported.supported)
        self.assertEqual(unsupported.status, "unsupported")


if __name__ == "__main__":
    unittest.main()
