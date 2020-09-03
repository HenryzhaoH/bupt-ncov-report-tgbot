import abc


class AbstractMigration(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, database, migrator):
        self._database = database
        self._migrator = migrator

    @abc.abstractmethod
    def migrate(self):
        pass

    @abc.abstractmethod
    def rollback(self):
        pass
