const appDb = process.env.MONGO_INITDB_DATABASE;
const appUser = process.env.MONGO_APP_USER;
const appPwd  = process.env.MONGO_APP_PWD;

print(`[init] creating app user '${appUser}' on db '${appDb}'`);

db = db.getSiblingDB(appDb);
db.createUser({
  user: appUser,
  pwd:  appPwd,
  roles: [{ role: "readWrite", db: appDb }]
});

print(`[init] creating index on 'battles' collection for 'battleTime' and 'referencePlayerTag'`);

db.battles.createIndex(
  { referencePlayerTag: 1, battleTime: -1 },
  { unique: true, name: "referencePlayerTag_battleTime_index" }
);