# Backup & restore

State lives in named Docker volumes. Back up **MySQL** (accounts, projects, nodes, run
history, beat schedule) and **Mongo** (per-account variables, published dashboards)
together, from a consistent point. Redis holds only in-flight queue state.

These commands are verified: a dump taken from a running stack restores cleanly onto
empty volumes with all projects, run history (DagRuns/NodeRuns) and stored values intact.

## Back up

```bash
PROJECT=wa-verify          # your compose project name
STAMP=$(date +%Y%m%d-%H%M%S)
mkdir -p backups/$STAMP

# MySQL (reads the root password from the container's own env)
docker exec ${PROJECT}-mysql-1 sh -c \
  'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --databases waveassist' \
  > backups/$STAMP/mysql.sql

# Mongo (all databases, single archive)
docker exec ${PROJECT}-mongo-1 sh -c 'exec mongodump --archive' \
  > backups/$STAMP/mongo.archive
```

Store `backups/$STAMP/` off-host. For a clean snapshot of a busy system, disarm
schedules (or stop `beat`/`worker`) briefly so no run is mid-write during the dump.

## Restore (onto a fresh/empty deployment)

```bash
PROJECT=wa-verify
SRC=backups/<stamp>

# Start only the datastores first (empty volumes), and WAIT until MySQL is truly ready
docker compose -p $PROJECT up -d mysql mongo
until docker exec ${PROJECT}-mysql-1 sh -c 'mysqladmin ping -uroot -p"$MYSQL_ROOT_PASSWORD"' >/dev/null 2>&1; do sleep 3; done

# MySQL (the dump recreates the `waveassist` database)
docker exec -i ${PROJECT}-mysql-1 sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD"' < $SRC/mysql.sql

# Mongo
docker cp $SRC/mongo.archive ${PROJECT}-mongo-1:/tmp/mongo.archive
docker exec ${PROJECT}-mongo-1 mongorestore --drop --archive=/tmp/mongo.archive

# Then bring up the rest
docker compose -p $PROJECT up -d
```

> Wait for the MySQL readiness loop above before restoring — restoring while the server
> is still initialising fails partway (observed as a first-run error that succeeds on retry).

## Verify a restore

```bash
docker exec ${PROJECT}-mysql-1 sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -N -e "
  SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=\"waveassist\";
  SELECT project_key FROM waveassist.WaveAssist_Project;
  SELECT COUNT(*) FROM waveassist.WaveAssist_DagRuns;"'
# Mongo: a per-account db is wa_<first-20-chars-of-uid>
docker exec ${PROJECT}-mongo-1 mongosh --quiet wa_<uid20> --eval \
  'db.getCollectionNames().forEach(c=>print(c, db[c].countDocuments()))'
```

## Redis durability

Redis carries broker/result state and the camera event bus, not primary data. The
compose `redis` service mounts a `redis_data` volume, but define a durability policy
explicitly (e.g. `--appendonly yes`) if you need in-flight runs to survive a restart;
otherwise treat Redis as ephemeral and re-trigger any run that was in flight at crash
time. Beat schedules live in MySQL, so schedules survive regardless.

## Migration to one host (hosted consolidation)

1. Take consistent MySQL + Mongo backups from the source (RDS + Atlas).
2. Stand up the box with `WA_BOOTSTRAP_ADMIN=0` and datastores only.
3. Restore both dumps (above), then apply migrations: `docker compose up -d api`
   runs `manage.py migrate` on boot (migration 0068 adds `Project.local_configuration`
   and node source paths; it is additive and safe on populated data).
4. Map existing per-account queues to the shared queue and set provider URLs/keys.
5. Bring up one scheduler last; verify runs, then cut DNS over. Keep the old stack
   drained (schedulers/workers stopped) during overlap to avoid duplicate sends.
