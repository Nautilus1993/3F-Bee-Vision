import sqlite3
import os
import hashlib
import numpy as np
import cv2
import pdb

class DataStorage:
    def __init__(self, db_name):
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()

    def createTable(self):
        try:
            sql1 = '''
            CREATE TABLE IF NOT EXISTS `info`(
                `id` VARCHAR(32) PRIMARY KEY,
                `time_s` INTEGER UNSIGNED NOT NULL,
                `time_ms` INTEGER UNSIGNED NOT NULL,
                `local_time` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                `width` INTEGER NOT NULL,
                `height` INTEGER NOT NULL,
                `exposure` INTEGER NOT NULL,
                `class` INTEGER NOT NULL,
                `score` REAL NOT NULL
            );
            '''
            sql2 = '''
            CREATE TABLE IF NOT EXISTS `source`(
                `id` VARCHAR(32) PRIMARY KEY,
                `data` BLOB NOT NULL,
                `thumbnail` BLOB NOT NULL,
                FOREIGN KEY(`id`) REFERENCES `info`(`id`) ON DELETE CASCADE ON DELETE CASCADE
            );
            '''
            self.cursor.execute(sql1)
            self.cursor.execute(sql2)
            return 1
        except Exception as e:
            print('>> Creat Error:', e)
            return 0

  
    def _insertInfo(self, table_name, data):
        keys = ', '.join(data.keys())
        values = ', '.join([f'"{v}"' for v in data.values()])
        sql = f'INSERT INTO {table_name} ({keys}) VALUES ({values});'
        self.cursor.execute(sql)
        self.conn.commit()
    
    def _insertSource(self, id, data, thumbnail):
        self.cursor.execute('INSERT INTO source (id, data, thumbnail) VALUES (?, ?, ?);', (id, data, thumbnail))
        self.conn.commit()

    def _query(self, table_name, fields, condition=None, order=None, limit=None, group=None):
        field_str = ', '.join(fields)
        sql = f'SELECT {field_str} FROM {table_name}'
        if condition is not None:
            sql += f' WHERE {condition}'
        if order is not None:
            sql += f' ORDER BY {order}'
        if limit is not None:
            sql += f' LIMIT {limit}'
        if group is not None:
            sql += f' GROUP BY {group}'
        # print(sql)
        self.cursor.execute(sql)
        return self.cursor.fetchall()


    def close(self):
        self.conn.close()

    def delete(self, table_name):
        sql = f'DROP TABLE IF EXISTS {table_name}'
        self.cursor.execute(sql)
        self.conn.commit()

    def update(self, table_name, data, condition):
        data_str = ', '.join([f'{k}="{v}"' for k, v in data.items()])
        sql = f'UPDATE {table_name} SET {data_str} WHERE {condition}'
        self.cursor.execute(sql)
        self.conn.commit()

    def __del__(self):
        self.conn.close()

    def insert(self, time_s, time_ms, width, height, exposure, class_type, score, data):
        thumbnail = cv2.resize(data, (128, 128))
        thumbnail = cv2.imencode('.jpg', thumbnail)[1].tobytes()
        data = cv2.imencode('.jpg', data)[1].tobytes()
        id = hashlib.md5(data).hexdigest()
        self._insertInfo('info', {'id': id, 'time_s': time_s, 'time_ms': time_ms, 'width': width, 'height': height, 'exposure': exposure, 'class': class_type, 'score': score})
        self._insertSource(id, data, thumbnail)

    def queryByScore(self, count=3):
        info = self._query('info', ['id', 'time_s', 'time_ms', 'width', 'height', 'exposure', 'class', 'score'], order = 'score', limit=count)
        for res in info:
            id = res[0]
            data = self._query('source', ['data'], f'id = \'{id}\'')
            print(len(data))
            print(len(data[0]))
            data = np.frombuffer(data[0][0], np.uint8)
            data = cv2.imdecode(data, cv2.IMREAD_COLOR)
            # cv2.imwrite(f'{id}.jpg', data)
        return info
    
    def queryIDThumbnailByClass(self, class_type):
        ids = self._query('info', ['id'], condition=f'class = {class_type}')
        ids = np.array(ids).reshape(-1).tolist()
        return self._query('source', ['id', 'thumbnail'], condition=f'id in {ids}'.replace('[','(').replace(']',')'))

    def queryByIDSortByScoreLimitByCount(self, ids, count=1):
        info =  self._query('info', ['id', 'time_s', 'time_ms', 'width', 'height', 'exposure', 'class', 'score'], \
                           condition=f'id in {ids}'.replace('[','(').replace(']',')'), order='score', limit=count)
        data = None
        for res in info:
            id = res[0]
            data = self._query('source', ['data'], f'id = \'{id}\'')
            data = np.frombuffer(data[0][0], np.uint8)
            data = cv2.imdecode(data, cv2.IMREAD_COLOR)
        
        return info, data


# # invoke once
def init_database():
    db = DataStorage('./data/m3.db')
    db.createTable()
    db.close()


# def test():
#     db = DataStorage('./data/m3.db')
#     # db.insert(686, 900, 1024, 1024, 500, 1, 1.4523, cv2.imread('test.jpg'))
#     db.queryByScore()

if __name__ == '__main__':
    init_database()
    # test()
