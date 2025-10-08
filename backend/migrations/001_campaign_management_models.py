"""
Campaign Management Models Migration
Creates and updates tables for campaign management functionality
"""

from flask_migrate import upgrade, downgrade
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

def upgrade():
    """Apply migration changes"""
    
    # Update campaigns table with new columns and indexes
    with op.batch_alter_table('campaigns', schema=None) as batch_op:
        # Add new columns
        batch_op.add_column(sa.Column('target_identifier', sa.String(255), nullable=True))
        batch_op.add_column(sa.Column('started_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('completed_at', sa.DateTime(), nullable=True))
        
        # Modify existing columns
        batch_op.alter_column('name', existing_type=sa.String(200), type_=sa.String(255))
        batch_op.alter_column('target_type', nullable=False)
        batch_op.alter_column('message_template', nullable=False)
        
        # Add indexes for performance
        batch_op.create_index('ix_campaigns_user_id', ['user_id'])
        batch_op.create_index('ix_campaigns_twitter_account_id', ['twitter_account_id'])
        batch_op.create_index('ix_campaigns_status', ['status'])
        batch_op.create_index('ix_campaigns_created_at', ['created_at'])
    
    # Update campaign_targets table with new columns and indexes
    with op.batch_alter_table('campaign_targets', schema=None) as batch_op:
        # Add new columns
        batch_op.add_column(sa.Column('twitter_user_id', sa.String(50), nullable=True))
        batch_op.add_column(sa.Column('profile_picture', sa.String(500), nullable=True))
        batch_op.add_column(sa.Column('follower_count', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('is_verified', sa.Boolean(), nullable=True, default=False))
        batch_op.add_column(sa.Column('can_dm', sa.Boolean(), nullable=True, default=True))
        batch_op.add_column(sa.Column('error_message', sa.Text(), nullable=True))
        
        # Modify existing columns
        batch_op.alter_column('username', existing_type=sa.String(50), type_=sa.String(255))
        batch_op.alter_column('display_name', existing_type=sa.String(100), type_=sa.String(255))
        batch_op.alter_column('twitter_user_id', nullable=False)
        
        # Add indexes for performance
        batch_op.create_index('ix_campaign_targets_campaign_id', ['campaign_id'])
        batch_op.create_index('ix_campaign_targets_twitter_user_id', ['twitter_user_id'])
        batch_op.create_index('ix_campaign_targets_username', ['username'])
        batch_op.create_index('ix_campaign_targets_follower_count', ['follower_count'])
        batch_op.create_index('ix_campaign_targets_is_verified', ['is_verified'])
        batch_op.create_index('ix_campaign_targets_status', ['status'])
        batch_op.create_index('ix_campaign_targets_created_at', ['created_at'])
    
    # Create campaign_messages table
    op.create_table('campaign_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=False),
        sa.Column('target_id', sa.Integer(), nullable=False),
        sa.Column('message_content', sa.Text(), nullable=False),
        sa.Column('twitter_message_id', sa.String(50), nullable=True),
        sa.Column('status', sa.String(20), nullable=True, default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('replied_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ),
        sa.ForeignKeyConstraint(['target_id'], ['campaign_targets.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add indexes to campaign_messages table
    with op.batch_alter_table('campaign_messages', schema=None) as batch_op:
        batch_op.create_index('ix_campaign_messages_campaign_id', ['campaign_id'])
        batch_op.create_index('ix_campaign_messages_target_id', ['target_id'])
        batch_op.create_index('ix_campaign_messages_twitter_message_id', ['twitter_message_id'])
        batch_op.create_index('ix_campaign_messages_status', ['status'])
        batch_op.create_index('ix_campaign_messages_created_at', ['created_at'])

def downgrade():
    """Revert migration changes"""
    
    # Drop campaign_messages table
    op.drop_table('campaign_messages')
    
    # Revert campaign_targets table changes
    with op.batch_alter_table('campaign_targets', schema=None) as batch_op:
        # Drop indexes
        batch_op.drop_index('ix_campaign_targets_created_at')
        batch_op.drop_index('ix_campaign_targets_status')
        batch_op.drop_index('ix_campaign_targets_is_verified')
        batch_op.drop_index('ix_campaign_targets_follower_count')
        batch_op.drop_index('ix_campaign_targets_username')
        batch_op.drop_index('ix_campaign_targets_twitter_user_id')
        batch_op.drop_index('ix_campaign_targets_campaign_id')
        
        # Drop new columns
        batch_op.drop_column('error_message')
        batch_op.drop_column('can_dm')
        batch_op.drop_column('is_verified')
        batch_op.drop_column('follower_count')
        batch_op.drop_column('profile_picture')
        batch_op.drop_column('twitter_user_id')
        
        # Revert column changes
        batch_op.alter_column('display_name', existing_type=sa.String(255), type_=sa.String(100))
        batch_op.alter_column('username', existing_type=sa.String(255), type_=sa.String(50))
    
    # Revert campaigns table changes
    with op.batch_alter_table('campaigns', schema=None) as batch_op:
        # Drop indexes
        batch_op.drop_index('ix_campaigns_created_at')
        batch_op.drop_index('ix_campaigns_status')
        batch_op.drop_index('ix_campaigns_twitter_account_id')
        batch_op.drop_index('ix_campaigns_user_id')
        
        # Drop new columns
        batch_op.drop_column('completed_at')
        batch_op.drop_column('started_at')
        batch_op.drop_column('target_identifier')
        
        # Revert column changes
        batch_op.alter_column('message_template', nullable=True)
        batch_op.alter_column('target_type', nullable=True)
        batch_op.alter_column('name', existing_type=sa.String(255), type_=sa.String(200))