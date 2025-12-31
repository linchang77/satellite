import json
import psycopg2
from psycopg2 import extras

# 1. 数据库连接配置 (根据你的实际情况修改)
conn_config = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "weixingyunyuansheng",
    "host": "localhost",
    "port": "5432"
}

def import_satellite_data(json_file_path):
    # 读取 JSON 文件
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    meta = data['meta']
    sats = data['satellites']

    try:
        conn = psycopg2.connect(**conn_config)
        cur = conn.cursor()

        # 2. 插入场景表 (Scenarios)
        # 注意：sensor_config 使用 json.dumps 转为字符串存入 JSONB 字段
        insert_scenario_query = """
        INSERT INTO scenarios (name, epoch, start_time, end_time, alt_km, inc_deg, n_planes, n_sats_per_plane, sensor_config)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
        """
        cur.execute(insert_scenario_query, (
            meta['scenario'],
            meta['epoch'].replace(" UTCG", ""), # 简单清理时间格式
            meta['timePeriod']['start'],
            meta['timePeriod']['end'],
            meta['constellation']['altKm'],
            meta['constellation']['incDeg'],
            meta['constellation']['nPlanes'],
            meta['constellation']['nSatsPerPlane'],
            json.dumps(meta['sensor'])
        ))
        
        scenario_id = cur.fetchone()[0]
        print(f"成功创建场景，ID 为: {scenario_id}")

        # 3. 批量插入卫星表 (Satellites)
        # 准备数据元组列表
        sat_records = []
        for s in sats:
            orb = s['orbit']
            sat_records.append((
                scenario_id,
                s['satId'],
                s['stkName'],
                s['planeIndex'],
                s['satIndexInPlane'],
                orb['altKm'],
                orb['smaKm'],
                orb['ecc'],
                orb['incDeg'],
                orb['raanDeg'],
                orb['argpDeg'],
                orb['taDeg']
            ))

        insert_sat_query = """
        INSERT INTO satellites (
            scenario_id, sat_id, stk_name, plane_index, sat_index_in_plane,
            alt_km, sma_km, ecc, inc_deg, raan_deg, argp_deg, ta_deg
        ) VALUES %s;
        """
        
        # 使用 execute_values 进行高效批量插入
        extras.execute_values(cur, insert_sat_query, sat_records)
        
        conn.commit()
        print(f"成功导入 {len(sat_records)} 颗卫星数据！")

    except Exception as e:
        print(f"发生错误: {e}")
        if conn: conn.rollback()
    finally:
        if cur: cur.close()
        if conn: conn.close()

# 运行脚本
if __name__ == "__main__":
    import_satellite_data('starlink_shell1_36x22.json') # 换成你的文件名