
from cStringIO import StringIO
from persistent import Persistent
from repozitory.interfaces import IArchive
from repozitory.interfaces import IAttachment
from repozitory.interfaces import IObjectHistoryRecord
from repozitory.interfaces import IObjectVersion
from repozitory.schema import ArchivedAttachment
from repozitory.schema import ArchivedBlob
from repozitory.schema import ArchivedChunk
from repozitory.schema import ArchivedClass
from repozitory.schema import ArchivedCurrent
from repozitory.schema import ArchivedObject
from repozitory.schema import ArchivedState
from repozitory.schema import Base
from sqlalchemy import func
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm.session import sessionmaker
from zope.interface import implements
from zope.sqlalchemy import ZopeTransactionExtension
import datetime
import hashlib
import tempfile

_global_session_cache = {}  # {db_string: SQLAlchemy session}


def clear_session_cache():
    _global_session_cache.clear()


class EngineParams(Persistent):
    """Parameters to pass to SQLAlchemy's create_engine() call.

    db_string is an URL such as postgresql://localhost:5432/ .
    The keyword parameters are documented here:

    http://www.sqlalchemy.org/docs/core/engines.html#sqlalchemy.create_engine
    """
    def __init__(self, db_string, **kwargs):
        self.db_string = db_string
        self.kwargs = kwargs


def unicode_or_none(s):
    return unicode(s) if s is not None else None


def find_class(module, name):
    m = __import__(module, None, None, ('__doc__',))
    return getattr(m, name, None)


class Archive(Persistent):
    """An object archive that uses SQLAlchemy."""
    implements(IArchive)

    _v_session = None
    chunk_size = 1048576

    def __init__(self, engine_params):
        self.engine_params = engine_params

    @property
    def session(self):
        """Get the SQLAlchemy session."""
        session = self._v_session
        if session is None:
            params = self.engine_params
            db_string = params.db_string
            session = _global_session_cache.get(db_string)
            if session is None:
                engine = create_engine(db_string, **params.kwargs)
                session = self._create_session(engine)
                _global_session_cache[db_string] = session
            self._v_session = session
        return session

    def _create_session(self, engine):
        Base.metadata.create_all(engine)
        # Distinguish sessions by thread.
        session = scoped_session(sessionmaker(
            extension=ZopeTransactionExtension()))
        session.configure(bind=engine)
        return session

    def archive(self, obj, user, comment=None):
        """Add a version to the archive of an object.

        The object does not need to have been in the archive
        previously.  The object must either implement or be adaptable
        to IObjectIdentity and IObjectContent.

        Returns the new version number.
        """
        obj = IObjectVersion(obj)

        docid = obj.docid
        session = self.session
        prev_version = None
        arc_obj = (session.query(ArchivedObject)
            .filter_by(docid=docid)
            .first())
        if arc_obj is None:
            arc_obj = ArchivedObject(
                docid=docid,
                created=obj.created,
            )
            session.add(arc_obj)
        else:
            (prev_version,) = (
                session.query(func.max(ArchivedState.version_num))
                .filter_by(docid=docid)
                .one())

        klass = getattr(obj, 'klass', None)
        if klass is None:
            klass = obj.__class__
        class_id = self._prepare_class_id(klass)

        arc_state = ArchivedState(
            docid=docid,
            version_num=(prev_version or 0) + 1,
            archive_time=datetime.datetime.utcnow(),
            class_id=class_id,
            path=unicode(obj.path),
            modified=obj.modified,
            user=unicode(user),
            title=unicode_or_none(obj.title),
            description=unicode_or_none(obj.description),
            attrs=obj.attrs,
            comment=unicode_or_none(comment),
        )
        session.add(arc_state)

        attachments = getattr(obj, 'attachments', None)
        if attachments:
            for name, value in attachments.items():
                self._attach(arc_state, name, value)

        arc_current = (
            session.query(ArchivedCurrent)
            .filter_by(docid=docid)
            .first())
        if arc_current is None:
            arc_current = ArchivedCurrent(
                docid=docid,
                version_num=arc_state.version_num,
            )
            session.add(arc_current)
        else:
            arc_current.version_num = arc_state.version_num
        session.flush()
        return arc_state.version_num

    def _prepare_class_id(self, klass):
        """Add a class or reuse an existing class ID."""
        session = self.session
        module = unicode(klass.__module__)
        name = unicode(klass.__name__)
        actual = find_class(module, name)
        if actual != klass:
            raise TypeError("Broken class reference: %s != %s" % (
                actual, klass))
        cls = (session.query(ArchivedClass)
            .filter_by(module=module, name=name)
            .first())
        if cls is None:
            cls = ArchivedClass(module=module, name=name)
            session.add(cls)
            session.flush()
        return cls.class_id

    def _attach(self, arc_state, name, value):
        """Add a named attachment to an object state."""
        if IAttachment.providedBy(value):
            content_type = getattr(value, 'content_type', None)
            attrs = getattr(value, 'attrs', None)
            f = value.file
        else:
            content_type = None
            attrs = None
            f = value
        if isinstance(f, basestring):
            fn = f
            f = open(fn, 'rb')
            try:
                blob_id = self._prepare_blob_id(f)
            finally:
                f.close()
        else:
            f.seek(0)
            blob_id = self._prepare_blob_id(f)

        a = ArchivedAttachment(
            docid=arc_state.docid,
            version_num=arc_state.version_num,
            name=unicode(name),
            content_type=unicode_or_none(content_type),
            blob_id=blob_id,
            attrs=attrs,
        )
        arc_state.attachments.append(a)

    def _prepare_blob_id(self, f):
        """Upload a blob or reuse an existing blob containing the same data."""
        # Compute the length and hashes of the blob data.
        length = 0
        md5_calc = hashlib.md5()
        sha256_calc = hashlib.sha256()
        while True:
            data = f.read(self.chunk_size)
            if not data:
                break
            length += len(data)
            md5_calc.update(data)
            sha256_calc.update(data)
        md5 = md5_calc.hexdigest()
        sha256 = sha256_calc.hexdigest()
        f.seek(0)

        session = self.session
        arc_blob = (
            session.query(ArchivedBlob)
            .filter_by(length=length, md5=md5, sha256=sha256)
            .first())
        if arc_blob is not None:
            return arc_blob.blob_id

        arc_blob = ArchivedBlob(
            chunk_count=0,
            length=length,
            md5=md5,
            sha256=sha256,
        )
        session.add(arc_blob)
        session.flush()  # Assign arc_blob.blob_id
        blob_id = arc_blob.blob_id

        # Upload the data.
        chunk_index = 0
        while True:
            data = f.read(self.chunk_size)
            if not data:
                break
            arc_chunk = ArchivedChunk(
                blob_id=blob_id,
                chunk_index=chunk_index,
                chunk_length=len(data),
                data=data,
            )
            arc_blob.chunks.append(arc_chunk)
            session.flush()
            chunk_index += 1

        arc_blob.chunk_count = chunk_index
        session.flush()
        return arc_blob.blob_id

    def history(self, docid):
        """Get the history of an object.

        Returns a list of objects that provide IObjectHistoryRecord.
        The most recent version is listed first.
        """
        created = (self.session.query(ArchivedObject)
            .filter_by(docid=docid)
            .one()).created
        current_version = (self.session.query(ArchivedCurrent)
            .filter_by(docid=docid)
            .one()).version_num
        rows = (self.session.query(ArchivedState)
            .filter_by(docid=docid)
            .order_by(ArchivedState.version_num)
            .all())
        return [ObjectHistoryRecord(row, created, current_version)
            for row in rows]


class ObjectHistoryRecord(object):
    implements(IObjectHistoryRecord)

    _attachments = None
    _klass = None

    def __init__(self, state, created, current_version):
        self._state = state
        self.current_version = current_version
        self.created = created
        self.modified = state.modified
        self.title = state.title
        self.description = state.description
        self.docid = state.docid
        self.path = state.path
        self.attrs = state.attrs
        self.version_num = state.version_num
        self.archive_time = state.archive_time
        self.user = state.user
        self.comment = state.comment

    @property
    def attachments(self):
        if self._attachments is not None:
            return self._attachments
        res = {}
        for a in self._state.attachments:
            res[a.name] = AttachmentInfo(a)
        self._attachments = res
        return res

    @property
    def klass(self):
        res = self._klass
        if res is None:
            cls = self._state.class_
            self._klass = res = find_class(cls.module, cls.name)
        return res


class AttachmentInfo(object):
    implements(IAttachment)

    _memory_limit = 1048576

    def __init__(self, attachment):
        self._attachment = attachment
        self.content_type = attachment.content_type
        self.attrs = attachment.attrs

    @property
    def file(self):
        length = self._attachment.blob.length
        if length <= self._memory_limit:
            # The attachment fits in memory.
            f = StringIO()
        else:
            # Write the attachment to a temporary file.
            f = tempfile.TemporaryFile()
        for chunk in self._attachment.blob.chunks:
            f.write(chunk.data)
        f.seek(0)
        return f
