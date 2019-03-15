
from contextlib import contextmanager
from time import time

from sqlalchemy import Column, Integer, UniqueConstraint
from sqlalchemy.sql.functions import count

from ..types import Time, ShortCls, Str, short_cls
from ..support import Base


class Timestamp(Base):

    '''
    This was introduced to simplify tracking dependencies for statistics.

    For example, we only need to re-calculate summary statistics for data that are newer than the latest
    summary.

    Previously, dependencies were managed by complex logic (outer joins with missing values) that were
    hard to write and hard to understand later.  Also, they had the following problems:

    * Trying to re-calculate heart rate statistics when the "missing" values are caused by the activity
      having no HRM data.

    * Nearby activities being restricted to geographic regions, making it hard to decide if all relevant
      activities were included.
    '''

    __tablename__ = 'timestamp'

    id = Column(Integer, primary_key=True)
    time = Column(Time, nullable=False, default=time)
    owner = Column(ShortCls, nullable=False)
    constraint = Column(Str)
    key = Column(Integer)
    UniqueConstraint(owner, constraint, key)

    @classmethod
    def set(cls, log, s, owner, constraint=None, key=None):
        cls.clear(s, owner, constraint=constraint, key=key)
        s.add(Timestamp(owner=owner, constraint=constraint, key=key))
        s.commit()
        log.debug(f'Timestamp for {short_cls(owner)} / {key}')

    @classmethod
    def get(cls, s, owner, constraint=None, key=None):
        return s.query(Timestamp). \
            filter(Timestamp.owner == owner,
                   Timestamp.constraint == constraint,
                   Timestamp.key == key).one_or_none()

    @classmethod
    def clear(cls, s, owner, constraint=None, key=None):
        exists = cls.get(s, owner, constraint=constraint, key=key)
        if exists:
            s.delete(exists)

    @classmethod
    def clean_keys(cls, log, s, keep, owner, constraint=None):
        s.commit()
        for repeat in range(2):
            q = s.query(Timestamp if repeat else count(Timestamp.id)). \
                filter(~Timestamp.key.in_(keep),
                       Timestamp.owner == owner,
                       Timestamp.constraint == constraint)
            if repeat:
                q.delete(synchronize_session=False)
            else:
                log.debug(f'Clearing {q.scalar()} Timestamps for {short_cls(owner)} / {constraint}')

    @classmethod
    def clear_after(cls, s, time, owner, constraint=None):
        q = s.query(Timestamp). \
            filter(Timestamp.owner == owner,
                   Timestamp.constraint == constraint)
        if time:
            q = q.filter(Timestamp.time >= time)
        q.delete()

    @contextmanager
    def on_success(self, log, s):
        self.clear(s, self.owner, constraint=self.constraint, key=self.key)
        yield None
        self.set(log, s, self.owner, constraint=self.constraint, key=self.key)

