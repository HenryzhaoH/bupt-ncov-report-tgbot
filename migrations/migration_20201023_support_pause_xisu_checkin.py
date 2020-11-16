from include import *
from peewee import SqliteDatabase
from playhouse.migrate import *
from migrations.MigrationBase import AbstractMigration

import os

'''
Intended for server started before xisu_checkin was added

'''


class AddXisuCheckinAbstractMigration(AbstractMigration):
    def migrate(self):
        with self._database.atomic():
            migrate(
                self._migrator.add_column(
                    table='buptuser',
                    column_name='xisu_checkin_status',
                    field=BUPTUser.xisu_checkin_status
                ),
            )
            print(f'{__file__} migrated')

    def rollback(self):
        with self._database.atomic():
            migrate(
                self._migrator.drop_column(table='buptuser', column_name='xisu_checkin_status'),
            )
            print(f'{__file__} rolled back')


if __name__ == '__main__':
    os.chdir(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))

    database = SqliteDatabase(SQLITE_DB_FILE_PATH)
    migrator = SqliteMigrator(database)

    migration = AddXisuCheckinAbstractMigration(database=database, migrator=migrator)

    migration.migrate()
    # migration.rollback()
