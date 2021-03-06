import unittest
from types import MappingProxyType
from typing import KeysView

from itemadapter.adapter import ItemAdapter

from tests import (
    AttrsItem,
    AttrsItemNested,
    DataClassItem,
    DataClassItemNested,
    ScrapySubclassedItem,
    ScrapySubclassedItemNested,
)


class ItemAdapterReprTestCase(unittest.TestCase):
    def test_repr_dict(self):
        item = dict(name="asdf", value=1234)
        adapter = ItemAdapter(item)
        # dicts are not guarantied to be sorted in py35
        self.assertTrue(
            repr(adapter) == "<ItemAdapter for dict(name='asdf', value=1234)>"
            or repr(adapter) == "<ItemAdapter for dict(value=1234, name='asdf')>",
        )

    @unittest.skipIf(not ScrapySubclassedItem, "scrapy module is not available")
    def test_repr_scrapy_item(self):
        item = ScrapySubclassedItem(name="asdf", value=1234)
        adapter = ItemAdapter(item)
        # Scrapy fields are stored in a dict, which is not guarantied to be sorted in py35
        self.assertTrue(
            repr(adapter) == "<ItemAdapter for ScrapySubclassedItem(name='asdf', value=1234)>"
            or repr(adapter) == "<ItemAdapter for ScrapySubclassedItem(value=1234, name='asdf')>",
        )

    @unittest.skipIf(not DataClassItem, "dataclasses module is not available")
    def test_repr_dataclass(self):
        item = DataClassItem(name="asdf", value=1234)
        adapter = ItemAdapter(item)
        self.assertEqual(
            repr(adapter), "<ItemAdapter for DataClassItem(name='asdf', value=1234)>",
        )

    def test_repr_attrs(self):
        item = AttrsItem(name="asdf", value=1234)
        adapter = ItemAdapter(item)
        self.assertEqual(
            repr(adapter), "<ItemAdapter for AttrsItem(name='asdf', value=1234)>",
        )


class ItemAdapterInitError(unittest.TestCase):
    def test_non_item(self):
        with self.assertRaises(TypeError):
            ItemAdapter(ScrapySubclassedItem)
        with self.assertRaises(TypeError):
            ItemAdapter(dict)
        with self.assertRaises(TypeError):
            ItemAdapter(1234)


class BaseTestMixin:

    item_class = None
    item_class_nested = None

    def setUp(self):
        if self.item_class is None:
            raise unittest.SkipTest()

    def test_get_set_value(self):
        item = self.item_class()
        adapter = ItemAdapter(item)
        self.assertEqual(adapter.get("name"), None)
        self.assertEqual(adapter.get("value"), None)
        adapter["name"] = "asdf"
        adapter["value"] = 1234
        self.assertEqual(adapter.get("name"), "asdf")
        self.assertEqual(adapter.get("value"), 1234)
        self.assertEqual(adapter["name"], "asdf")
        self.assertEqual(adapter["value"], 1234)

        item = self.item_class(name="asdf", value=1234)
        adapter = ItemAdapter(item)
        self.assertEqual(adapter.get("name"), "asdf")
        self.assertEqual(adapter.get("value"), 1234)
        self.assertEqual(adapter["name"], "asdf")
        self.assertEqual(adapter["value"], 1234)

    def test_get_value_keyerror(self):
        item = self.item_class()
        adapter = ItemAdapter(item)
        with self.assertRaises(KeyError):
            adapter["undefined_field"]

    def test_as_dict(self):
        item = self.item_class(name="asdf", value=1234)
        adapter = ItemAdapter(item)
        self.assertEqual(dict(name="asdf", value=1234), dict(adapter))

    def test_as_dict_nested(self):
        item = self.item_class_nested(
            nested=self.item_class(name="asdf", value=1234),
            adapter=ItemAdapter(dict(foo="bar", nested_list=[1, 2, 3, 4, 5])),
            dict_={"foo": "bar", "answer": 42, "nested_dict": {"a": "b"}},
            list_=[1, 2, 3],
            set_={1, 2, 3},
            tuple_=(1, 2, 3),
            int_=123,
        )
        adapter = ItemAdapter(item)
        self.assertEqual(
            adapter.asdict(),
            dict(
                nested=dict(name="asdf", value=1234),
                adapter=dict(foo="bar", nested_list=[1, 2, 3, 4, 5]),
                dict_={"foo": "bar", "answer": 42, "nested_dict": {"a": "b"}},
                list_=[1, 2, 3],
                set_={1, 2, 3},
                tuple_=(1, 2, 3),
                int_=123,
            ),
        )

    def test_field_names(self):
        item = self.item_class(name="asdf", value=1234)
        adapter = ItemAdapter(item)
        self.assertIsInstance(adapter.field_names(), KeysView)
        self.assertEqual(sorted(adapter.field_names()), ["name", "value"])


class NonDictTestMixin(BaseTestMixin):
    def test_set_value_keyerror(self):
        item = self.item_class()
        adapter = ItemAdapter(item)
        with self.assertRaises(KeyError):
            adapter["undefined_field"] = "some value"

    def test_metadata_common(self):
        adapter = ItemAdapter(self.item_class())
        self.assertIsInstance(adapter.get_field_meta("name"), MappingProxyType)
        self.assertIsInstance(adapter.get_field_meta("value"), MappingProxyType)
        with self.assertRaises(KeyError):
            adapter.get_field_meta("undefined_field")

    def test_get_field_meta_defined_fields(self):
        adapter = ItemAdapter(self.item_class())
        self.assertEqual(adapter.get_field_meta("name"), MappingProxyType({"serializer": str}))
        self.assertEqual(adapter.get_field_meta("value"), MappingProxyType({"serializer": int}))

    def test_delitem_len_iter(self):
        item = self.item_class(name="asdf", value=1234)
        adapter = ItemAdapter(item)
        self.assertEqual(len(adapter), 2)
        self.assertEqual(sorted(list(iter(adapter))), ["name", "value"])

        del adapter["name"]
        self.assertEqual(len(adapter), 1)
        self.assertEqual(sorted(list(iter(adapter))), ["value"])

        del adapter["value"]
        self.assertEqual(len(adapter), 0)
        self.assertEqual(sorted(list(iter(adapter))), [])

        with self.assertRaises(KeyError):
            del adapter["name"]
        with self.assertRaises(KeyError):
            del adapter["value"]
        with self.assertRaises(KeyError):
            del adapter["undefined_field"]


class DictTestCase(unittest.TestCase, BaseTestMixin):

    item_class = dict
    item_class_nested = dict

    def test_get_value_keyerror_item_dict(self):
        """Instantiate without default values"""
        adapter = ItemAdapter(self.item_class())
        with self.assertRaises(KeyError):
            adapter["name"]

    def test_empty_metadata(self):
        adapter = ItemAdapter(self.item_class(name="foo", value=5))
        for field_name in ("name", "value", "undefined_field"):
            self.assertEqual(adapter.get_field_meta(field_name), MappingProxyType({}))

    def test_field_names_updated(self):
        item = self.item_class(name="asdf")
        field_names = ItemAdapter(item).field_names()
        self.assertEqual(sorted(field_names), ["name"])
        item["value"] = 1234
        self.assertEqual(sorted(field_names), ["name", "value"])


class ScrapySubclassedItemTestCase(NonDictTestMixin, unittest.TestCase):

    item_class = ScrapySubclassedItem
    item_class_nested = ScrapySubclassedItemNested

    def test_get_value_keyerror_item_dict(self):
        """Instantiate without default values"""
        adapter = ItemAdapter(self.item_class())
        with self.assertRaises(KeyError):
            adapter["name"]


class DataClassItemTestCase(NonDictTestMixin, unittest.TestCase):

    item_class = DataClassItem
    item_class_nested = DataClassItemNested


class AttrsItemTestCase(NonDictTestMixin, unittest.TestCase):

    item_class = AttrsItem
    item_class_nested = AttrsItemNested
