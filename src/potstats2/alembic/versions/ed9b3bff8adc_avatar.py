"""Avatar

Revision ID: ed9b3bff8adc
Revises: 7b4028b44355
Create Date: 2018-06-30 11:40:10.779229

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ed9b3bff8adc'
down_revision = '7b4028b44355'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('avatars',
    sa.Column('avid', sa.Integer(), autoincrement=False, nullable=False),
    sa.Column('path', sa.Unicode(), nullable=False),
    sa.PrimaryKeyConstraint('avid', name=op.f('pk_avatars'))
    )
    op.add_column('users', sa.Column('avid', sa.Integer(), nullable=True))
    op.create_foreign_key(op.f('fk_users_avid_avatars'), 'users', 'avatars', ['avid'], ['avid'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(op.f('fk_users_avid_avatars'), 'users', type_='foreignkey')
    op.drop_column('users', 'avid')
    op.drop_table('avatars')
    # ### end Alembic commands ###
