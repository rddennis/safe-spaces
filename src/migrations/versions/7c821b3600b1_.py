"""empty message

Revision ID: 7c821b3600b1
Revises: d62be1b2690b
Create Date: 2016-10-17 15:27:33.138783

"""

# revision identifiers, used by Alembic.
revision = '7c821b3600b1'
down_revision = 'd62be1b2690b'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('friends',
    sa.Column('friend_id', sa.Integer(), nullable=True),
    sa.Column('friended_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['friend_id'], ['user.id'], ),
    sa.ForeignKeyConstraint(['friended_id'], ['user.id'], )
    )
    op.add_column(u'user', sa.Column('username', sa.String(length=255), nullable=True))
    op.create_unique_constraint(None, 'user', ['username'])
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'user', type_='unique')
    op.drop_column(u'user', 'username')
    op.drop_table('friends')
    ### end Alembic commands ###
