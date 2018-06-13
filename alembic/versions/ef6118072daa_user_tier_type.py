"""user_tier_type

Revision ID: ef6118072daa
Revises: 910adb215219
Create Date: 2018-06-13 21:41:12.637541

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ef6118072daa'
down_revision = '910adb215219'
branch_labels = None
depends_on = None

tiertype = sa.Enum('standard', 'special', name='tiertype')


def upgrade():
    tiertype.create(op.get_bind())
    op.add_column('user_tiers', sa.Column('type', tiertype, nullable=True))
    op.create_index('uniq', 'user_tiers', ['name', 'bars', 'type'], unique=True)


def downgrade():
    op.drop_index('uniq', table_name='user_tiers')
    op.drop_column('user_tiers', 'type')
    tiertype.drop(op.get_bind())
