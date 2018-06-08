from ets.ets_mysql_lib import MysqlConnection as Mc
import ets.ets_email_lib as email
from ets.ets_xml_worker import EIS_HEADERS
from itertools import count
from time import sleep
from os.path import join, normpath, exists
from queries import *
from config import *
import logger_module
import requests
import json
import re


MAIL_TEXT = ''
SQL_TEXT = ''
C_COUNT = 0

tmp_html = join(normpath(tmp_dir), tmp_html)
tmp_sql = join(normpath(tmp_dir), tmp_sql)
tmp_json = join(normpath(tmp_dir), tmp_json)

counter = count(start=1, step=1)
cn_44 = Mc(connection=Mc.MS_44_2_CONNECT)


def main():
    global MAIL_TEXT, SQL_TEXT, C_COUNT
    # получаем данные json если есть откуда, если нет, то создаем файл с пустым дампом
    if not exists(tmp_json):
        json_loads_data = []
        with open(tmp_json, mode='w') as tmp_json_f:
            tmp_json_f.write(json.dumps(json_loads_data))
    else:
        with open(tmp_json, mode='r') as tmp_json_f:
            tmp_json_r = tmp_json_f.read()
        json_loads_data = json.loads(tmp_json_r)

    # получаем данные о новых опубликованных процедурах
    with cn_44.open():
        procedures_data = cn_44.execute_query(get_procedures_data_query, query_interval, dicted=True)

    for procedure in procedures_data:
        procedure['need_correct'] = False

        with open(tmp_html, mode='wb') as w_tmp:
            try:
                w_tmp.write(requests.get(procedure['urlPrintForm'], headers=EIS_HEADERS, timeout=(1, 3)).content)
            except requests.exceptions.ReadTimeout:
                logger.info('%s %s' % (procedure['registrationNumber'], 'ReadTimeout'))
                continue
            except requests.exceptions.ConnectTimeout:
                logger.info('%s %s' % (procedure['registrationNumber'], 'ConnectTimeout'))
                continue

        with open(tmp_html, mode='r', encoding='utf8') as r_tmp:
            eis_xml = r_tmp.read()

        try:
            procedure['specOrgRegNum'] = re.findall(
                r'<specializedOrgInfo>.*?<regNum>(.*?)</regNum>.*?</specializedOrgInfo>',
                eis_xml,
                re.MULTILINE | re.DOTALL)[0]
        except IndexError:
            procedure['specOrgRegNum'] = None

        # если найден specOrgRegNum
        if procedure['specOrgRegNum']:

            with cn_44.open():
                try:
                    procedure['specOrgId'] = cn_44.execute_query(
                        get_organization_id_query % procedure['specOrgRegNum'][1:])[0][0]
                except IndexError:
                    procedure['specOrgId'] = None

            if not procedure['customerId'] and procedure['placerId'] and procedure['specOrgId']:
                procedure['update_query'] = \
                    'Невозможно сформировать запрос для корректировки %(registrationNumber)s' % procedure
                continue

            json_info = '_'.join((str(procedure['id']), str(procedure['version'])))

            if not (procedure['customerId'] == procedure['placerId'] == procedure['specOrgId']) \
                    and (json_info not in json_loads_data):

                json_loads_data.append(json_info)
                procedure['need_correct'] = True
                procedure['order_num'] = C_COUNT = next(counter)
                procedure['update_query'] = '''UPDATE procedures p -- %(registrationNumber)s, placerId=%(placerId)s, customerId=%(customerId)s
    SET p.customerId = %(specOrgId)s, p.placerId = %(specOrgId)s, p.updateDateTime = NOW()
    WHERE p.id = %(id)s;\n\n''' % procedure

        if procedure['need_correct']:
            logger.warn('%(registrationNumber)s find spec_org=%(specOrgRegNum)s' % procedure)

        sleep(sleep_time)

    # если нет записей, которые необходимо скорректировать, то выходим
    if C_COUNT == 0:
        return

    MAIL_TEXT += 'Требуются корректировки по %s процедурам:\n\n' % C_COUNT
    procedures_data = filter(lambda d: d['need_correct'], procedures_data)
    for procedure in procedures_data:

        MAIL_TEXT += '''%(order_num)s) %(registrationNumber)s (%(editDateTime)s)\n''' % procedure
        SQL_TEXT += '%(update_query)s' % procedure

    with open(tmp_json, mode='w') as tmp_json_f:
        tmp_json_f.write(json.dumps(json_loads_data))

    with open(tmp_sql, mode='w', encoding='utf8') as o_sql:
        o_sql.write(SQL_TEXT)

    email.mail_sender(MAIL_THEME, MAIL_TEXT,
                      recipients=recipients,
                      add_files=(tmp_sql,),
                      report=True,
                      counter=C_COUNT,
                      datetime=True)

if __name__ == '__main__':
    logger = logger_module.logger()
    try:
        main()
        # если при исполнении будут исключения - кратко выводим на терминал, остальное - в лог
    except Exception as e:
        logger.fatal('Fatal error! Exit', exc_info=True)
        print('Critical error: %s' % e)
        print('More information in log file')
        exit(1)
exit(0)

