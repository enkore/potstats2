"""Move advanced user attrs to main User class

Revision ID: f9bc9b5d8a2c
Revises: d90d40ba546f
Create Date: 2018-06-13 20:56:12.161182

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f9bc9b5d8a2c'
down_revision = 'd90d40ba546f'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('my_mods_users_tied_fkey', 'my_mods_users', type_='foreignkey')
    op.drop_column('my_mods_users', 'tied')
    op.drop_column('my_mods_users', 'last_seen')
    op.drop_column('my_mods_users', 'registered')
    op.drop_column('my_mods_users', 'account_state')
    op.drop_column('my_mods_users', 'online_status')
    op.drop_column('my_mods_users', 'locked_until')
    op.add_column('users', sa.Column('account_state', sa.Unicode(), nullable=True))
    op.add_column('users', sa.Column('last_seen', sa.TIMESTAMP(), nullable=True))
    op.add_column('users', sa.Column('locked_until', sa.Unicode(), nullable=True))
    op.add_column('users', sa.Column('online_status', sa.Unicode(), nullable=True))
    op.add_column('users', sa.Column('registered', sa.TIMESTAMP(), nullable=True))
    op.add_column('users', sa.Column('tied', sa.Integer(), nullable=True))
    op.create_foreign_key('users_tied_fkey', 'users', 'user_tiers', ['tied'], ['tied'])
    op.create_check_constraint(
        'complete_requires_closed',
        'users',
        "account_state = 'locked_temp' or locked_until is null",
    )


def downgrade():
    op.drop_constraint('complete_requires_closed', 'users')
    op.drop_constraint('users_tied_fkey', 'users', type_='foreignkey')
    op.drop_column('users', 'tied')
    op.drop_column('users', 'registered')
    op.drop_column('users', 'online_status')
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'last_seen')
    op.drop_column('users', 'account_state')
    op.add_column('my_mods_users', sa.Column('locked_until', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('my_mods_users', sa.Column('online_status', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('my_mods_users', sa.Column('account_state', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('my_mods_users', sa.Column('registered', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('my_mods_users', sa.Column('last_seen', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('my_mods_users', sa.Column('tied', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key('my_mods_users_tied_fkey', 'my_mods_users', 'user_tiers', ['tied'], ['tied'])
