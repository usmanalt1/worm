from django.db import migrations, models

# The new constraint cannot be added while a player still holds a row per team they have
# been snapshotted on, so the delete is part of the schema change rather than separate.
DROP_SUPERSEDED_ROWS = """
DELETE FROM teams_roster
WHERE id IN (
    SELECT id FROM (
        SELECT id, row_number() OVER (
            PARTITION BY player_id, season_id
            ORDER BY run_timestamp DESC NULLS LAST, id DESC
        ) AS rn
        FROM teams_roster
    ) ranked
    WHERE rn > 1
);
"""


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0025_martplayervolatility'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='teamroster',
            name='teams_roster_unique_team_player_season',
        ),
        migrations.RunSQL(DROP_SUPERSEDED_ROWS, reverse_sql=migrations.RunSQL.noop),
        migrations.AddConstraint(
            model_name='teamroster',
            constraint=models.UniqueConstraint(fields=('player_id', 'season_id'), name='teams_roster_unique_player_season'),
        ),
    ]
