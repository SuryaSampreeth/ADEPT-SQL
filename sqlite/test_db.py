from sqlalchemy import create_engine, MetaData, select,text
import pandas as pd

class localsqlite():
    def __init__(self, db_path):
        self.db_path = db_path
    
    def conn(self):
        self.engine =  create_engine(f"sqlite:///{self.db_path}")
        self.connection = self.engine.connect()
        self.metadata = MetaData()
        self.metadata.reflect(bind=self.connection)
        return self

class _localsqlite():
    def __init__(self, db_path):
        self.db_path = db_path
    def conn(self):
        self.connection = create_engine(f"sqlite:///{self.db_path}").connect()
        self.metadata = MetaData()
        self.metadata.reflect(bind=self.connection)
        return self

db = localsqlite("./cre_Drama_Workshop_Groups.sqlite").conn()
# get all table names
print(db.metadata.tables.keys())

# get all columns of table students

for column in db.metadata.tables["Clients"].columns:
    print(column)

# execute a query "SELECT * FROM students"
df = pd.read_sql_query(text("SELECT Client_ID FROM Clients"), db.engine)
print(df)