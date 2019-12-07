#!/usr/bin/env bash

# there are more things to edit at the end of this file

# you may want to change these variables

DB_DIR=~/.ch2
TMP_DIR=/tmp

SRC='0-27'
DST='0-28'

# these allow you to skip parts of the logic if re-doing a migration (expert only)
DO_COPY=1
DO_DROP=1
DO_DUMP=1


# this section of the script copies diary data and kit data across

if ((DO_COPY)); then
  echo "ensuring write-ahead file for $DB_DIR/database-$SRC.sql is cleared"
  echo "(should print 'delete')"
  sqlite3 "$DB_DIR/database-$SRC.sql" 'pragma journal_mode=delete' || { echo 'database locked?'; exit 1; }
  echo "copying data to $TMP_DIR/copy-$SRC.sql"
  rm -f "$TMP_DIR/copy-$SRC.sql"
  cp "$DB_DIR/database-$SRC.sql" "$TMP_DIR/copy-$SRC.sql"
fi

if ((DO_DROP)); then
  echo "dropping activity data from $TMP_DIR/copy-$SRC.sql"
  sqlite3 "$TMP_DIR/copy-$SRC.sql" <<EOF
  pragma foreign_keys = on;
  -- don't delete topic and kit data, and keep composite for next step
  delete from source where type not in (3, 9, 10, 7);
  -- clean composite data
  delete from source where id in (
    select id from (
      select composite_source.id, composite_source.n_components as target, count(composite_component.id) as actual
        from composite_source left outer join composite_component
          on composite_source.id = composite_component.output_source_id
       group by composite_component.id
    ) where target != actual
  );
  delete from source where id in (
    select id from composite_source where n_components = 0
  );
  delete from statistic_name where id in (
    select statistic_name.id from statistic_name
      left outer join statistic_journal
        on statistic_journal.statistic_name_id = statistic_name.id
     where statistic_journal.id is null
  );
  -- remove statistic names used by constants
  delete from statistic_name where owner = 'Constant';
  -- remove puns from package names
  update topic_field set display_cls = replace(display_cls, 'uweird', 'urwid');
  -- rename topic to diary_topic
  create table diary_topic (
        id integer not null,
        parent_id integer,
        schedule text not null,
        start integer,
        finish integer,
        name text default '' not null,
        description text default '' not null,
        sort integer default '' not null,
        primary key (id),
        foreign key(parent_id) references diary_topic (id)
  );
  create table diary_topic_field (
        id integer not null,
        diary_topic_id integer not null,
        type integer not null,
        sort integer,
        statistic_name_id integer not null,
        display_cls text not null,
        display_args text default '[]' not null,
        display_kargs text default '{}' not null,
        schedule text default '' not null,
        primary key (id),
        foreign key(diary_topic_id) references diary_topic (id) on delete cascade,
        foreign key(statistic_name_id) references statistic_name (id) on delete cascade
  );
  create table diary_topic_journal (
        id integer not null,
        diary_topic_id integer,
        date integer not null,
        primary key (id),
        foreign key(id) references source (id) on delete cascade,
        foreign key(diary_topic_id) references diary_topic (id)
  );
  create index ix_diary_topic_journal_date on diary_topic_journal (date);
  pragma foreign_keys = off;
  insert into diary_topic select * from topic;
  insert into diary_topic_field select * from topic_field;
  insert into diary_topic_journal select * from topic_journal;
  drop table topic;
  drop table topic_field;
  drop table topic_journal;
  pragma foreign_keys = on;
EOF
fi

if ((DO_DUMP)); then
  echo "extracting data from $TMP_DIR/copy-$SRC.sql to load into new database"
  rm -f "$TMP_DIR/dump-$SRC.sql"
  # .commands cannot be indented?!
  sqlite3 "$TMP_DIR/copy-$SRC.sql" <<EOF
.output $TMP_DIR/dump-$SRC.sql
.mode insert source
select * from source;
.mode insert composite_source
select * from composite_source;
.mode insert composite_component
select * from composite_component;
.mode insert statistic_journal
select * from statistic_journal;
.mode insert statistic_journal_float
select * from statistic_journal_float;
.mode insert statistic_journal_integer
select * from statistic_journal_integer;
.mode insert statistic_journal_text
select * from statistic_journal_text;
.mode insert statistic_journal_timestamp
select * from statistic_journal_timestamp;
.mode insert statistic_name
select * from statistic_name;
.mode insert diary_topic
select * from diary_topic;
.mode insert diary_topic_field
select * from diary_topic_field;
.mode insert diary_topic_journal
select * from diary_topic_journal;
.mode insert segment
select * from segment;
.mode insert kit_group
select * from kit_group;
.mode insert kit_item
select * from kit_item;
.mode insert kit_component
select * from kit_component;
.mode insert kit_model
select * from kit_model;
EOF
fi

echo "creating new, empty database at $DB_DIR/database-$DST.sql"
echo "(should print warning config message)"
rm -f "$DB_DIR/database-$DST.sql"
dev/ch2 no-op

echo "loading data into $DB_DIR/database-$DST.sql"
sqlite3 "$DB_DIR/database-$DST.sql" < "$TMP_DIR/dump-$SRC.sql"

echo "adding default config to $DB_DIR/database-$DST.sql"
dev/ch2 --dev config default --no-diary


# you almost certainly want to change the following details

echo "adding personal constants to $DB_DIR/database-$DST.sql"
dev/ch2 --dev constants set FTHR.Bike 154
dev/ch2 --dev constants set FTHR.Walk 154
dev/ch2 --dev constants set SRTM1.Dir /home/andrew/archive/srtm1
# the name of this constant depends on the kit name and so we must add it ourselves
dev/ch2 --dev constants add --single Power.cotic \
  --description 'Bike namedtuple values to calculate power for this kit' \
  --validate ch2.stats.calculate.power.Bike
dev/ch2 --dev constants set Power.cotic '{"cda": 0.42, "crr": 0.0055, "weight": 12}'


echo "next, run 'ch2 activities' or similar to load data"