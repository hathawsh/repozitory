"""Tests of repozitory.archive"""

from StringIO import StringIO
import datetime
import transaction
import unittest2 as unittest


class ArchiveTest(unittest.TestCase):

    def setUp(self):
        transaction.abort()

    def tearDown(self):
        transaction.abort()

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
        from repozitory.interfaces import IObjectVersion
        from zope.interface import implements

        class DummyObjectVersion(object):
            implements(IObjectVersion)
            docid = 4
            path = '/my/object'
            created = datetime.datetime(2011, 4, 6)
            modified = datetime.datetime(2011, 4, 7)
            title = 'Cool Object'
            description = None
            attrs = {'a': 1, 'b': [2]}

        return DummyObjectVersion()

    def test_verifyImplements_IArchive(self):
        from zope.interface.verify import verifyClass
        from repozitory.interfaces import IArchive
        verifyClass(IArchive, self._class())

    def test_verifyProvides_IArchive(self):
        from zope.interface.verify import verifyObject
        from repozitory.interfaces import IArchive
        verifyObject(IArchive, self._make_default())

    def test_verifyImplements_IPersistent(self):
        from zope.interface.verify import verifyClass
        from persistent.interfaces import IPersistent
        verifyClass(IPersistent, self._class())

    def test_verifyProvides_IPersistent(self):
        from zope.interface.verify import verifyObject
        from persistent.interfaces import IPersistent
        verifyObject(IPersistent, self._make_default())

    def test_query_session_with_empty_database(self):
        from repozitory.schema import ArchivedObject
        archive = self._make_default()
        session = archive.session
        q = session.query(ArchivedObject).count()
        self.assertEqual(q, 0)

    def test_archive_simple_object(self):
        obj = self._make_dummy_object_version()
        archive = self._make_default()
        archive.archive(obj, 'tester', 'I like version control.')

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

        from repozitory.schema import ArchivedBlob
        rows = archive.session.query(ArchivedBlob).all()
        self.assertEqual(len(rows), 0)

        from repozitory.schema import ArchivedChunk
        rows = archive.session.query(ArchivedChunk).all()
        self.assertEqual(len(rows), 0)

        from repozitory.schema import ArchivedAttachment
        rows = archive.session.query(ArchivedAttachment).all()
        self.assertEqual(len(rows), 0)

        from repozitory.schema import ArchivedContainer
        rows = archive.session.query(ArchivedContainer).all()
        self.assertEqual(len(rows), 0)

        from repozitory.schema import ArchivedContainerItem
        rows = archive.session.query(ArchivedContainerItem).all()
        self.assertEqual(len(rows), 0)

    def test_archive_2_revisions_of_simple_object(self):
        obj = self._make_dummy_object_version()
        archive = self._make_default()
        archive.archive(obj, 'tester', 'I like version control.')
        obj.title = 'New Title!'
        archive.archive(obj, 'tester', 'I still like version control.')

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

    def test_archive_with_simple_attachment(self):
        obj = self._make_dummy_object_version()
        obj.attachments = {'readme.txt': StringIO('42')}
        archive = self._make_default()
        archive.archive(obj, 'tester')

        from repozitory.schema import ArchivedBlob
        rows = archive.session.query(ArchivedBlob).all()
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

        from repozitory.schema import ArchivedAttachment
        rows = archive.session.query(ArchivedAttachment).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].docid, 4)
        self.assertEqual(rows[0].version_num, 1)
        self.assertEqual(rows[0].name, 'readme.txt')
        self.assertEqual(rows[0].content_type, None)
        self.assertEqual(rows[0].attrs, None)

    def test_archive_with_complex_attachment(self):
        from zope.interface import implements
        from repozitory.interfaces import IAttachment

        class DummyAttachment(object):
            implements(IAttachment)
            file = StringIO('42')
            content_type = 'text/plain'
            attrs = {'_MACOSX': {'icon': 'apple-ownz-u'}}

        obj = self._make_dummy_object_version()
        obj.attachments = {'readme.txt': DummyAttachment()}
        archive = self._make_default()
        archive.archive(obj, 'tester')

        from repozitory.schema import ArchivedAttachment
        rows = archive.session.query(ArchivedAttachment).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].docid, 4)
        self.assertEqual(rows[0].version_num, 1)
        self.assertEqual(rows[0].name, 'readme.txt')
        self.assertEqual(rows[0].content_type, u'text/plain')
        self.assertEqual(rows[0].attrs, {'_MACOSX': {'icon': 'apple-ownz-u'}})

    def test_archive_with_filename_attachment(self):
        import tempfile
        f = tempfile.NamedTemporaryFile()
        f.write('42')
        f.flush()

        obj = self._make_dummy_object_version()
        obj.attachments = {'readme.txt': f.name}
        archive = self._make_default()
        archive.archive(obj, 'tester')

        from repozitory.schema import ArchivedChunk
        rows = archive.session.query(ArchivedChunk).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].chunk_index, 0)
        self.assertEqual(rows[0].data, '42')

        from repozitory.schema import ArchivedAttachment
        rows = archive.session.query(ArchivedAttachment).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].docid, 4)
        self.assertEqual(rows[0].version_num, 1)
        self.assertEqual(rows[0].name, 'readme.txt')
        self.assertEqual(rows[0].content_type, None)
        self.assertEqual(rows[0].attrs, None)

    def test_archive_deduplicates_attachments(self):
        obj = self._make_dummy_object_version()
        obj.attachments = {'readme.txt': StringIO('42')}
        archive = self._make_default()
        archive.archive(obj, 'tester')

        obj.attachments['readme2.txt'] = StringIO('24.')
        archive.archive(obj, 'tester')

        from repozitory.schema import ArchivedBlob
        rows = (archive.session.query(ArchivedBlob)
            .order_by(ArchivedBlob.length)
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

        from repozitory.schema import ArchivedAttachment
        rows = (archive.session.query(ArchivedAttachment)
            .order_by(ArchivedAttachment.version_num, ArchivedAttachment.name)
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

    def test_archive_object_that_fails_to_adapt_to_IObjectVersion(self):
        archive = self._make_default()
        with self.assertRaises(TypeError):
            archive.archive(object(), 'tester')