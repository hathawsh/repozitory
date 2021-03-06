"""Tests of repozitory.archive"""

from StringIO import StringIO
import datetime
import unittest2 as unittest


class ArchiveTest(unittest.TestCase):

    def setUp(self):
        import transaction
        transaction.abort()
        from repozitory.archive import forget_sessions
        forget_sessions()

    def tearDown(self):
        import transaction
        transaction.abort()
        from repozitory.archive import forget_sessions
        forget_sessions()

    def _class(self):
        from repozitory.archive import Archive
        return Archive

    def _make(self, *args, **kw):
        return self._class()(*args, **kw)

    def _make_default(self):
        from repozitory.archive import EngineParams
        params = EngineParams('sqlite:///')
        return self._make(params)

    def _make_dummy_object_version(self):
        return DummyObjectVersion()

    def test_verifyImplements_IArchive(self):
        from zope.interface.verify import verifyClass
        from repozitory.interfaces import IArchive
        verifyClass(IArchive, self._class())

    def test_verifyProvides_IArchive(self):
        from zope.interface.verify import verifyObject
        from repozitory.interfaces import IArchive
        verifyObject(IArchive, self._make_default())

    def test_query_session_with_empty_database(self):
        from repozitory.schema import ArchivedObject
        archive = self._make_default()
        session = archive.session
        q = session.query(ArchivedObject).count()
        self.assertEqual(q, 0)

    def test_archive_simple_object(self):
        obj = self._make_dummy_object_version()
        archive = self._make_default()
        ver = archive.archive(obj)
        self.assertEqual(ver, 1)

        from repozitory.schema import ArchivedObject
        rows = archive.session.query(ArchivedObject).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].docid, 4)
        self.assertEqual(rows[0].created, datetime.datetime(2011, 4, 6))

        from repozitory.schema import ArchivedClass
        rows = archive.session.query(ArchivedClass).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].module, u'repozitory.tests.test_archive')
        self.assertEqual(rows[0].name, u'DummyObjectVersion')

        from repozitory.schema import ArchivedState
        rows = archive.session.query(ArchivedState).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].docid, 4)
        self.assertEqual(rows[0].version_num, 1)
        self.assertEqual(rows[0].path, u'/my/object')
        self.assertEqual(rows[0].modified, datetime.datetime(2011, 4, 7))
        self.assertEqual(rows[0].title, u'Cool Object')
        self.assertEqual(rows[0].description, None)
        self.assertEqual(rows[0].attrs, {'a': 1, 'b': [2]})
        self.assertEqual(rows[0].comment, u'I like version control.')

        from repozitory.schema import ArchivedCurrent
        rows = archive.session.query(ArchivedCurrent).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].docid, 4)
        self.assertEqual(rows[0].version_num, 1)

        from repozitory.schema import ArchivedBlobInfo
        rows = archive.session.query(ArchivedBlobInfo).all()
        self.assertEqual(len(rows), 0)

        from repozitory.schema import ArchivedChunk
        rows = archive.session.query(ArchivedChunk).all()
        self.assertEqual(len(rows), 0)

        from repozitory.schema import ArchivedBlobLink
        rows = archive.session.query(ArchivedBlobLink).all()
        self.assertEqual(len(rows), 0)

        from repozitory.schema import ArchivedContainer
        rows = archive.session.query(ArchivedContainer).all()
        self.assertEqual(len(rows), 0)

        from repozitory.schema import ArchivedItem
        rows = archive.session.query(ArchivedItem).all()
        self.assertEqual(len(rows), 0)

        from repozitory.schema import ArchivedItemDeleted
        rows = archive.session.query(ArchivedItemDeleted).all()
        self.assertEqual(len(rows), 0)

    def test_archive_object_with_no_attrs(self):
        obj = self._make_dummy_object_version()
        obj.attrs = None
        archive = self._make_default()
        ver = archive.archive(obj)
        self.assertEqual(ver, 1)

        from repozitory.schema import ArchivedState
        rows = archive.session.query(ArchivedState).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].docid, 4)
        self.assertEqual(rows[0].version_num, 1)
        self.assertEqual(rows[0].path, u'/my/object')
        self.assertEqual(rows[0].modified, datetime.datetime(2011, 4, 7))
        self.assertEqual(rows[0].title, u'Cool Object')
        self.assertEqual(rows[0].description, None)
        self.assertEqual(rows[0].attrs, None)
        self.assertEqual(rows[0].comment, u'I like version control.')

    def test_archive_2_revisions_of_simple_object(self):
        obj = self._make_dummy_object_version()
        archive = self._make_default()
        v1 = archive.archive(obj)
        self.assertEqual(v1, 1)

        obj.title = 'New Title!'
        obj.comment = 'I still like version control.'
        v2 = archive.archive(obj)
        self.assertEqual(v2, 2)

        from repozitory.schema import ArchivedObject
        rows = archive.session.query(ArchivedObject).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].docid, 4)
        self.assertEqual(rows[0].created, datetime.datetime(2011, 4, 6))

        from repozitory.schema import ArchivedClass
        rows = archive.session.query(ArchivedClass).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].module, u'repozitory.tests.test_archive')
        self.assertEqual(rows[0].name, u'DummyObjectVersion')

        from repozitory.schema import ArchivedState
        rows = (archive.session.query(ArchivedState)
            .order_by(ArchivedState.version_num)
            .all())
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].docid, 4)
        self.assertEqual(rows[0].version_num, 1)
        self.assertEqual(rows[0].path, u'/my/object')
        self.assertEqual(rows[0].modified, datetime.datetime(2011, 4, 7))
        self.assertEqual(rows[0].title, u'Cool Object')
        self.assertEqual(rows[0].description, None)
        self.assertEqual(rows[0].attrs, {'a': 1, 'b': [2]})
        self.assertEqual(rows[0].comment, u'I like version control.')
        self.assertEqual(rows[1].docid, 4)
        self.assertEqual(rows[1].version_num, 2)
        self.assertEqual(rows[1].path, u'/my/object')
        self.assertEqual(rows[1].modified, datetime.datetime(2011, 4, 7))
        self.assertEqual(rows[1].title, u'New Title!')
        self.assertEqual(rows[1].description, None)
        self.assertEqual(rows[1].attrs, {'a': 1, 'b': [2]})
        self.assertEqual(rows[1].comment, u'I still like version control.')

        from repozitory.schema import ArchivedCurrent
        rows = archive.session.query(ArchivedCurrent).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].docid, 4)
        self.assertEqual(rows[0].version_num, 2)

    def test_archive_with_blob(self):
        obj = self._make_dummy_object_version()
        obj.blobs = {'readme.txt': StringIO('42')}
        archive = self._make_default()
        archive.archive(obj)

        from repozitory.schema import ArchivedBlobInfo
        rows = archive.session.query(ArchivedBlobInfo).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].chunk_count, 1)
        self.assertEqual(rows[0].length, 2)
        self.assertEqual(rows[0].md5,
            'a1d0c6e83f027327d8461063f4ac58a6')
        self.assertEqual(rows[0].sha256,
            '73475cb40a568e8da8a045ced110137e159f890ac4da883b6b17dc651b3a8049')

        from repozitory.schema import ArchivedChunk
        rows = archive.session.query(ArchivedChunk).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].chunk_index, 0)
        self.assertEqual(rows[0].data, '42')

        from repozitory.schema import ArchivedBlobLink
        rows = archive.session.query(ArchivedBlobLink).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].docid, 4)
        self.assertEqual(rows[0].version_num, 1)
        self.assertEqual(rows[0].name, 'readme.txt')

    def test_archive_with_filename_blob(self):
        import tempfile
        f = tempfile.NamedTemporaryFile()
        f.write('42')
        f.flush()

        obj = self._make_dummy_object_version()
        obj.blobs = {'readme.txt': f.name}
        archive = self._make_default()
        archive.archive(obj)

        from repozitory.schema import ArchivedChunk
        rows = archive.session.query(ArchivedChunk).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].chunk_index, 0)
        self.assertEqual(rows[0].data, '42')

        from repozitory.schema import ArchivedBlobLink
        rows = archive.session.query(ArchivedBlobLink).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].docid, 4)
        self.assertEqual(rows[0].version_num, 1)
        self.assertEqual(rows[0].name, 'readme.txt')

    def test_archive_deduplicates_blobs(self):
        obj = self._make_dummy_object_version()
        obj.blobs = {'readme.txt': StringIO('42')}
        archive = self._make_default()
        archive.archive(obj)
        obj.blobs['readme2.txt'] = StringIO('24.')
        archive.archive(obj)

        from repozitory.schema import ArchivedBlobInfo
        rows = (archive.session.query(ArchivedBlobInfo)
            .order_by(ArchivedBlobInfo.length)
            .all())
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].length, 2)
        self.assertEqual(rows[1].length, 3)

        from repozitory.schema import ArchivedChunk
        from sqlalchemy import func
        rows = (archive.session.query(ArchivedChunk)
            .order_by(func.length(ArchivedChunk.data))
            .all())
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].chunk_index, 0)
        self.assertEqual(rows[0].data, '42')
        self.assertEqual(rows[1].chunk_index, 0)
        self.assertEqual(rows[1].data, '24.')

        from repozitory.schema import ArchivedBlobLink
        rows = (archive.session.query(ArchivedBlobLink)
            .order_by(ArchivedBlobLink.version_num, ArchivedBlobLink.name)
            .all())
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0].docid, 4)
        self.assertEqual(rows[0].version_num, 1)
        self.assertEqual(rows[0].name, 'readme.txt')
        self.assertEqual(rows[1].docid, 4)
        self.assertEqual(rows[1].version_num, 2)
        self.assertEqual(rows[1].name, 'readme.txt')
        self.assertEqual(rows[2].docid, 4)
        self.assertEqual(rows[2].version_num, 2)
        self.assertEqual(rows[2].name, 'readme2.txt')

        # Confirm that rows 0 and 1, which are different versions,
        # refer to the same blob_id.
        self.assertEqual(rows[0].blob_id, rows[1].blob_id)
        # Row 2 refers to a different blob.
        self.assertNotEqual(rows[0].blob_id, rows[2].blob_id)

    def test_archive_broken_class(self):
        class Unpickleable:
            # Instances of this class should not be stored because the
            # class can not be resolved through a module and name reference.
            pass

        obj = self._make_dummy_object_version()
        obj.klass = Unpickleable
        archive = self._make_default()
        with self.assertRaises(TypeError):
            archive.archive(obj)

    def test_history_item_implements_IObjectHistoryRecord(self):
        obj = self._make_dummy_object_version()
        obj.comment = 'change 1'
        archive = self._make_default()
        archive.archive(obj)

        records = archive.history(obj.docid)
        self.assertEqual(len(records), 1)

        from zope.interface.verify import verifyObject
        from repozitory.interfaces import IObjectHistoryRecord
        verifyObject(IObjectHistoryRecord, records[0])

    def test_history_without_blobs(self):
        obj = self._make_dummy_object_version()
        obj.comment = 'change 1'
        archive = self._make_default()
        archive.archive(obj)
        obj.title = 'Changed Title'
        obj.description = 'New Description'
        obj.modified = datetime.datetime(2011, 4, 11)
        obj.user = 'mixer upper'
        obj.comment = None
        archive.archive(obj)

        records = archive.history(obj.docid)
        self.assertEqual(len(records), 2)

        self.assertEqual(records[0].docid, 4)
        self.assertEqual(records[0].path, u'/my/object')
        self.assertEqual(records[0].created, datetime.datetime(2011, 4, 6))
        self.assertEqual(records[0].modified, datetime.datetime(2011, 4, 11))
        self.assertEqual(records[0].version_num, 2)
        self.assertEqual(records[0].current_version, 2)
        self.assertEqual(records[0].title, u'Changed Title')
        self.assertEqual(records[0].description, u'New Description')
        self.assertEqual(records[0].attrs, {'a': 1, 'b': [2]})
        self.assertEqual(records[0].user, 'mixer upper')
        self.assertEqual(records[0].comment, None)
        self.assertFalse(records[0].blobs)
        self.assertEqual(records[0].klass, DummyObjectVersion)

        self.assertEqual(records[1].docid, 4)
        self.assertEqual(records[1].path, u'/my/object')
        self.assertEqual(records[1].created, datetime.datetime(2011, 4, 6))
        self.assertEqual(records[1].modified, datetime.datetime(2011, 4, 7))
        self.assertEqual(records[1].version_num, 1)
        self.assertEqual(records[1].current_version, 2)
        self.assertEqual(records[1].title, u'Cool Object')
        self.assertEqual(records[1].description, None)
        self.assertEqual(records[1].attrs, {'a': 1, 'b': [2]})
        self.assertEqual(records[1].user, 'tester')
        self.assertEqual(records[1].comment, 'change 1')
        self.assertFalse(records[1].blobs)
        self.assertEqual(records[1].klass, DummyObjectVersion)

        self.assertGreater(records[0].archive_time, records[0].created)

    def test_history_with_small_blob(self):
        obj = self._make_dummy_object_version()
        archive = self._make_default()
        archive.archive(obj)
        obj.blobs = {'x': StringIO('42')}
        archive.archive(obj)

        from repozitory.schema import ArchivedChunk
        rows = archive.session.query(ArchivedChunk).all()
        self.assertEqual(len(rows), 1)

        records = archive.history(obj.docid)
        self.assertEqual(len(records), 2)

        self.assertTrue(records[0].blobs)
        self.assertEqual(records[0].blobs.keys(), ['x'])
        blob = records[0].blobs['x']
        self.assertEqual(blob.read(), '42')
        with self.assertRaises(IOError):
            blob.write('x')
        with self.assertRaises(IOError):
            blob.writelines(['x'])

        self.assertFalse(records[1].blobs)

    def test_history_with_blob_having_multiple_chunks(self):
        archive = self._make_default()
        archive.chunk_size = 13
        obj = self._make_dummy_object_version()
        expect_blob = 'Abcdefghijk' * 7
        obj.blobs = {'x': StringIO(expect_blob)}
        archive.archive(obj)

        from repozitory.schema import ArchivedChunk
        rows = archive.session.query(ArchivedChunk).all()
        self.assertEqual(len(rows), 6)

        records = archive.history(obj.docid)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].blobs.keys(), ['x'])
        actual_blob = records[0].blobs['x'].read()
        self.assertEqual(len(actual_blob), len(expect_blob))
        self.assertEqual(actual_blob, expect_blob)

    def test_history_only_current(self):
        archive = self._make_default()
        obj = self._make_dummy_object_version()
        archive.archive(obj)
        obj.attrs = None
        archive.archive(obj)

        records = archive.history(obj.docid, only_current=True)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].attrs, {})

    def test_get_version(self):
        archive = self._make_default()
        obj = self._make_dummy_object_version()
        archive.archive(obj)
        obj.attrs = None
        archive.archive(obj)

        v1 = archive.get_version(obj.docid, 1)
        v2 = archive.get_version(obj.docid, 2)
        self.assertEqual(v1.attrs, {u'a': 1, u'b': [2]})
        self.assertEqual(v2.attrs, {})
        self.assertEqual(v1.version_num, 1)
        self.assertEqual(v2.version_num, 2)
        self.assertEqual(v1.current_version, 2)
        self.assertEqual(v2.current_version, 2)

    def test_reverted(self):
        obj = self._make_dummy_object_version()
        archive = self._make_default()
        v1 = archive.archive(obj)
        self.assertEqual(v1, 1)

        obj.title = 'New Title!'
        v2 = archive.archive(obj)
        self.assertEqual(v2, 2)

        records = archive.history(obj.docid)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].version_num, 2)
        self.assertEqual(records[1].version_num, 1)
        self.assertEqual(records[0].current_version, 2)
        self.assertEqual(records[1].current_version, 2)

        archive.reverted(obj.docid, 1)

        records = archive.history(obj.docid)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].version_num, 2)
        self.assertEqual(records[1].version_num, 1)
        self.assertEqual(records[0].current_version, 1)
        self.assertEqual(records[1].current_version, 1)

    def test_archive_container_empty(self):
        archive = self._make_default()

        class DummyContainerVersion:
            container_id = 5
            path = '/my/container'
            map = {}
            ns_map = {}

        archive.archive_container(DummyContainerVersion(), 'testuser')

        from repozitory.schema import ArchivedContainer
        rows = archive.session.query(ArchivedContainer).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].container_id, 5)
        self.assertEqual(rows[0].path, u'/my/container')

        from repozitory.schema import ArchivedItem
        rows = (archive.session.query(ArchivedItem)
            .order_by(ArchivedItem.namespace).all())
        self.assertEqual(len(rows), 0)

        from repozitory.schema import ArchivedItemDeleted
        rows = archive.session.query(ArchivedItemDeleted).all()
        self.assertEqual(len(rows), 0)

    def test_archive_container_non_empty(self):
        archive = self._make_default()
        obj4 = self._make_dummy_object_version()
        obj6 = self._make_dummy_object_version()
        obj6.docid = 6
        archive.archive(obj4)
        archive.archive(obj6)

        class DummyContainerVersion:
            container_id = 5
            path = '/my/container'
            map = {'a': 4}
            ns_map = {'headers': {'b': 6}}

        archive.archive_container(DummyContainerVersion(), 'testuser')

        from repozitory.schema import ArchivedContainer
        rows = archive.session.query(ArchivedContainer).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].container_id, 5)
        self.assertEqual(rows[0].path, u'/my/container')

        from repozitory.schema import ArchivedItem
        rows = (archive.session.query(ArchivedItem)
            .order_by(ArchivedItem.namespace).all())
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].container_id, 5)
        self.assertEqual(rows[0].namespace, u'')
        self.assertEqual(rows[0].name, u'a')
        self.assertEqual(rows[0].docid, 4)
        self.assertEqual(rows[1].container_id, 5)
        self.assertEqual(rows[1].namespace, u'headers')
        self.assertEqual(rows[1].name, u'b')
        self.assertEqual(rows[1].docid, 6)

        from repozitory.schema import ArchivedItemDeleted
        rows = archive.session.query(ArchivedItemDeleted).all()
        self.assertEqual(len(rows), 0)

    def test_archive_container_with_deletion(self):
        archive = self._make_default()
        obj4 = self._make_dummy_object_version()
        obj6 = self._make_dummy_object_version()
        obj6.docid = 6
        archive.archive(obj4)
        archive.archive(obj6)

        class DummyContainerVersion:
            container_id = 5
            path = '/my/container'
            map = {'a': 4}
            ns_map = {'headers': {'b': 6}}

        c = DummyContainerVersion()
        archive.archive_container(c, 'user1')
        c.ns_map = {}
        archive.archive_container(c, 'user2')

        from repozitory.schema import ArchivedContainer
        rows = archive.session.query(ArchivedContainer).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].container_id, 5)
        self.assertEqual(rows[0].path, u'/my/container')

        from repozitory.schema import ArchivedItem
        rows = archive.session.query(ArchivedItem).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].container_id, 5)
        self.assertEqual(rows[0].namespace, u'')
        self.assertEqual(rows[0].name, u'a')
        self.assertEqual(rows[0].docid, 4)

        from repozitory.schema import ArchivedItemDeleted
        rows = archive.session.query(ArchivedItemDeleted).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].container_id, 5)
        self.assertEqual(rows[0].namespace, u'headers')
        self.assertEqual(rows[0].name, u'b')
        self.assertEqual(rows[0].docid, 6)
        self.assertEqual(rows[0].deleted_by, 'user2')
        self.assertTrue(rows[0].deleted_time)

    def test_archive_container_with_undeletion(self):
        archive = self._make_default()
        obj4 = self._make_dummy_object_version()
        obj6 = self._make_dummy_object_version()
        obj6.docid = 6
        archive.archive(obj4)
        archive.archive(obj6)

        class DummyContainerVersion:
            container_id = 5
            path = '/my/container'
            map = {'a': 4}
            ns_map = {'headers': {'b': 6}}

        c = DummyContainerVersion()
        archive.archive_container(c, 'user1')
        c.ns_map = {}
        archive.archive_container(c, 'user2')
        c.ns_map = {'headers': {'z': 6}}
        archive.archive_container(c, 'user3')

        from repozitory.schema import ArchivedContainer
        rows = archive.session.query(ArchivedContainer).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].container_id, 5)
        self.assertEqual(rows[0].path, u'/my/container')

        from repozitory.schema import ArchivedItem
        rows = (archive.session.query(ArchivedItem)
            .order_by(ArchivedItem.namespace).all())
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].container_id, 5)
        self.assertEqual(rows[0].namespace, u'')
        self.assertEqual(rows[0].name, u'a')
        self.assertEqual(rows[0].docid, 4)
        self.assertEqual(rows[1].container_id, 5)
        self.assertEqual(rows[1].namespace, u'headers')
        self.assertEqual(rows[1].name, u'z')
        self.assertEqual(rows[1].docid, 6)

        from repozitory.schema import ArchivedItemDeleted
        rows = archive.session.query(ArchivedItemDeleted).all()
        self.assertEqual(len(rows), 0)

    def test_archive_container_with_no_change(self):
        archive = self._make_default()
        obj4 = self._make_dummy_object_version()
        obj6 = self._make_dummy_object_version()
        obj6.docid = 6
        archive.archive(obj4)
        archive.archive(obj6)

        class DummyContainerVersion:
            container_id = 5
            path = '/my/container'
            map = {'a': 4}
            ns_map = {'headers': {'b': 6}}

        c = DummyContainerVersion()
        archive.archive_container(c, 'user1')
        archive.archive_container(c, 'user2')

        from repozitory.schema import ArchivedContainer
        rows = archive.session.query(ArchivedContainer).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].container_id, 5)
        self.assertEqual(rows[0].path, u'/my/container')

        from repozitory.schema import ArchivedItem
        rows = (archive.session.query(ArchivedItem)
            .order_by(ArchivedItem.namespace).all())
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].container_id, 5)
        self.assertEqual(rows[0].namespace, u'')
        self.assertEqual(rows[0].name, u'a')
        self.assertEqual(rows[0].docid, 4)
        self.assertEqual(rows[1].container_id, 5)
        self.assertEqual(rows[1].namespace, u'headers')
        self.assertEqual(rows[1].name, u'b')
        self.assertEqual(rows[1].docid, 6)

        from repozitory.schema import ArchivedItemDeleted
        rows = archive.session.query(ArchivedItemDeleted).all()
        self.assertEqual(len(rows), 0)

    def test_archive_container_with_item_rename(self):
        archive = self._make_default()
        obj4 = self._make_dummy_object_version()
        obj6 = self._make_dummy_object_version()
        obj6.docid = 6
        archive.archive(obj4)
        archive.archive(obj6)

        class DummyContainerVersion:
            container_id = 5
            path = '/my/container'
            map = {'a': 4}
            ns_map = {'headers': {'b': 6}}

        c = DummyContainerVersion()
        archive.archive_container(c, 'user1')
        c.map = {'z': 4}
        archive.archive_container(c, 'user2')

        from repozitory.schema import ArchivedContainer
        rows = archive.session.query(ArchivedContainer).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].container_id, 5)
        self.assertEqual(rows[0].path, u'/my/container')

        from repozitory.schema import ArchivedItem
        rows = (archive.session.query(ArchivedItem)
            .order_by(ArchivedItem.namespace).all())
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].container_id, 5)
        self.assertEqual(rows[0].namespace, u'')
        self.assertEqual(rows[0].name, u'z')
        self.assertEqual(rows[0].docid, 4)
        self.assertEqual(rows[1].container_id, 5)
        self.assertEqual(rows[1].namespace, u'headers')
        self.assertEqual(rows[1].name, u'b')
        self.assertEqual(rows[1].docid, 6)

        from repozitory.schema import ArchivedItemDeleted
        rows = archive.session.query(ArchivedItemDeleted).all()
        self.assertEqual(len(rows), 0)

    def test_archive_container_with_path_change(self):
        archive = self._make_default()
        obj4 = self._make_dummy_object_version()
        archive.archive(obj4)

        class DummyContainerVersion:
            container_id = 5
            path = '/my/container'
            map = {'a': 4}
            ns_map = None

        c = DummyContainerVersion()
        archive.archive_container(c, 'user1')
        c.path = '/your/container'
        archive.archive_container(c, 'user2')

        from repozitory.schema import ArchivedContainer
        rows = archive.session.query(ArchivedContainer).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].container_id, 5)
        self.assertEqual(rows[0].path, u'/your/container')

        from repozitory.schema import ArchivedItem
        rows = (archive.session.query(ArchivedItem)
            .order_by(ArchivedItem.namespace).all())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].container_id, 5)
        self.assertEqual(rows[0].namespace, u'')
        self.assertEqual(rows[0].name, u'a')
        self.assertEqual(rows[0].docid, 4)

        from repozitory.schema import ArchivedItemDeleted
        rows = archive.session.query(ArchivedItemDeleted).all()
        self.assertEqual(len(rows), 0)

    def test_archive_container_with_changing_docid(self):
        archive = self._make_default()
        obj4 = self._make_dummy_object_version()
        obj6 = self._make_dummy_object_version()
        obj6.docid = 6
        archive.archive(obj4)
        archive.archive(obj6)

        class DummyContainerVersion:
            container_id = 5
            path = '/my/container'
            map = {'a': 4}
            ns_map = {'headers': {'b': 6}}

        c = DummyContainerVersion()
        archive.archive_container(c, 'user1')
        c.map = {'a': 6}
        archive.archive_container(c, 'user2')

        from repozitory.schema import ArchivedContainer
        rows = archive.session.query(ArchivedContainer).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].container_id, 5)
        self.assertEqual(rows[0].path, u'/my/container')

        from repozitory.schema import ArchivedItem
        rows = (archive.session.query(ArchivedItem)
            .order_by(ArchivedItem.namespace).all())
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].container_id, 5)
        self.assertEqual(rows[0].namespace, u'')
        self.assertEqual(rows[0].name, u'a')
        self.assertEqual(rows[0].docid, 6)
        self.assertEqual(rows[1].container_id, 5)
        self.assertEqual(rows[1].namespace, u'headers')
        self.assertEqual(rows[1].name, u'b')
        self.assertEqual(rows[1].docid, 6)

        from repozitory.schema import ArchivedItemDeleted
        rows = archive.session.query(ArchivedItemDeleted).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].container_id, 5)
        self.assertEqual(rows[0].namespace, u'')
        self.assertEqual(rows[0].name, u'a')
        self.assertEqual(rows[0].docid, 4)
        self.assertEqual(rows[0].deleted_by, 'user2')
        self.assertTrue(rows[0].deleted_time)

    def test_container_contents_empty(self):
        archive = self._make_default()

        class DummyContainerVersion:
            container_id = 5
            path = '/my/container'
            map = {}
            ns_map = {}

        archive.archive_container(DummyContainerVersion(), 'testuser')

        r = archive.container_contents(5)
        self.assertEqual(r.container_id, 5)
        self.assertEqual(r.path, u'/my/container')
        self.assertEqual(r.map, {})
        self.assertEqual(r.ns_map, {})
        self.assertEqual(r.deleted, [])

    def test_container_contents_non_empty(self):
        archive = self._make_default()
        obj4 = self._make_dummy_object_version()
        obj6 = self._make_dummy_object_version()
        obj6.docid = 6
        archive.archive(obj4)
        archive.archive(obj6)

        class DummyContainerVersion:
            container_id = 5
            path = '/my/container'
            map = {'a': 4}
            ns_map = {'headers': {'b': 6}}

        archive.archive_container(DummyContainerVersion(), 'testuser')

        r = archive.container_contents(5)

        from zope.interface.verify import verifyObject
        from repozitory.interfaces import IContainerRecord
        verifyObject(IContainerRecord, r)

        self.assertEqual(r.container_id, 5)
        self.assertEqual(r.path, u'/my/container')
        self.assertEqual(r.map, {'a': 4})
        self.assertEqual(r.ns_map, {'headers': {'b': 6}})
        self.assertEqual(r.deleted, [])

    def test_container_contents_with_deletion(self):
        archive = self._make_default()
        obj4 = self._make_dummy_object_version()
        obj6 = self._make_dummy_object_version()
        obj6.docid = 6
        archive.archive(obj4)
        archive.archive(obj6)

        class DummyContainerVersion:
            container_id = 5
            path = '/my/container'
            map = {'a': 4}
            ns_map = {'headers': {'b': 6}}

        c = DummyContainerVersion()
        archive.archive_container(c, 'user1')
        c.ns_map = {}
        archive.archive_container(c, 'user2')

        r = archive.container_contents(5)
        self.assertEqual(r.container_id, 5)
        self.assertEqual(r.path, u'/my/container')
        self.assertEqual(r.map, {'a': 4})
        self.assertEqual(r.ns_map, {})
        self.assertEqual(len(r.deleted), 1)

        row = r.deleted[0]
        from zope.interface.verify import verifyObject
        from repozitory.interfaces import IDeletedItem
        verifyObject(IDeletedItem, row)

        self.assertEqual(r.deleted[0].docid, 6)
        self.assertEqual(r.deleted[0].namespace, 'headers')
        self.assertEqual(r.deleted[0].name, 'b')
        self.assertEqual(r.deleted[0].deleted_by, 'user2')
        self.assertTrue(r.deleted[0].deleted_time)
        self.assertFalse(r.deleted[0].new_container_ids)

    def test_container_contents_after_move(self):
        archive = self._make_default()
        obj4 = self._make_dummy_object_version()
        archive.archive(obj4)

        class DummyContainerVersion:
            def __init__(self, container_id, path):
                self.container_id = container_id
                self.path = path
                self.map = {}
                self.ns_map = {}

        # user1 creates two containers, c5 and c6, putting obj4 in c5.
        c5 = DummyContainerVersion(5, '/c5')
        c5.map = {'a': 4}
        archive.archive_container(c5, 'user1')
        c6 = DummyContainerVersion(6, '/c6')
        archive.archive_container(c6, 'user1')

        # user2 moves obj4 from c5 to c6.
        c5.map = {}
        archive.archive_container(c5, 'user2')
        c6.map = {'a': 4}
        archive.archive_container(c6, 'user2')

        # List the contents of c5.  It should have a deletion record
        # with new_container_ids providing the new location of the object.
        r = archive.container_contents(5)
        self.assertEqual(r.container_id, 5)
        self.assertEqual(r.map, {})
        self.assertEqual(r.ns_map, {})
        self.assertEqual(len(r.deleted), 1)

        row = r.deleted[0]
        from zope.interface.verify import verifyObject
        from repozitory.interfaces import IDeletedItem
        verifyObject(IDeletedItem, row)

        self.assertEqual(r.deleted[0].docid, 4)
        self.assertEqual(r.deleted[0].namespace, '')
        self.assertEqual(r.deleted[0].name, 'a')
        self.assertEqual(r.deleted[0].deleted_by, 'user2')
        self.assertTrue(r.deleted[0].deleted_time)
        self.assertEqual(r.deleted[0].new_container_ids, [6])


class DummyObjectVersion:
    docid = 4
    path = '/my/object'
    created = datetime.datetime(2011, 4, 6)
    modified = datetime.datetime(2011, 4, 7)
    title = 'Cool Object'
    description = None
    attrs = {'a': 1, 'b': [2]}
    user = 'tester'
    comment = 'I like version control.'
