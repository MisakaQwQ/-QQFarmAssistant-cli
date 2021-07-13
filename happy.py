import requests
from selenium import webdriver
import time
import datetime
import json
import re
import os
import hashlib
import xml.sax
import xml.sax.handler
import prettytable as pt
from colorama import init, Fore, Back, Style
import random

API_addr = {
    'app_cfg': 'http://appbase.qzone.qq.com/cgi-bin/index/appbase_run_unity.cgi?appid=',
    'Farmland_stat': 'https://nc.qzone.qq.com/cgi-bin/cgi_farm_index',
    'Farmland_operation': 'https://nc.qzone.qq.com/cgi-bin/cgi_farm_opt',
    'Farmland_plant': 'https://nc.qzone.qq.com/cgi-bin/cgi_farm_plant',
    'Farmland_seed': 'https://farm.qzone.qq.com/cgi-bin/cgi_farm_getuserseed',
    'Farmland_buyseed': 'https://farm.qzone.qq.com/cgi-bin/cgi_farm_buyseed',
    'Wishtree_info': 'https://nc.qzone.qq.com/cgi-bin/cgi_farm_wish_index',
    'Wishtree_operation': 'https://nc.qzone.qq.com/cgi-bin/cgi_farm_wish_star',
    'Hive_info': 'https://nc.qzone.qq.com/cgi-bin/cgi_farm_hive_index',
    'Hive_harvest': 'https://nc.qzone.qq.com/cgi-bin/cgi_farm_hive_harvest',
    'Hive_work': 'https://nc.qzone.qq.com/cgi-bin/cgi_farm_hive_work',
}
init(autoreset=True)


class XMLHandler(xml.sax.handler.ContentHandler):
    def __init__(self):
        self.buffer = ""
        self.mapping = {}

    def startElement(self, name, attributes):
        self.buffer = ""

    def characters(self, data):
        self.buffer += data

    def endElement(self, name):
        self.mapping[name] = self.buffer

    def getDict(self):
        return self.mapping


class Bot:
    __session = requests.Session()
    __farm_appid = 353
    __uIdx = None
    __uinY = None
    __g_tk = None
    __p_skey = None
    stat_data = None
    history = []
    land = None
    bag = {}
    wishtree = {}
    hive = {}

    def get_crop_data(self):
        response = self.__session.get(API_addr['app_cfg'] + str(self.__farm_appid))
        flash_var = re.findall('var FLASH_VARS = {\n(.*)\n', response.text)[0].strip()
        flash_var = eval('{' + flash_var + '}')
        data_version = flash_var['crop_data'][flash_var['crop_data'].rfind('/') + 1:]
        if os.path.exists(data_version + '.json'):
            with open(data_version + '.json', 'r') as f:
                self.crop_data = json.load(f)
        else:
            raw_data = self.__session.get(flash_var['crop_data'])
            # XML method
            xh = XMLHandler()
            xml.sax.parseString(raw_data.text.encode(), xh)
            ret = xh.getDict()
            raw_data = eval(ret['crops'].strip())
            self.crop_data = {}
            for each in raw_data['crops']:
                self.crop_data[str(each['id'])] = each

            raw_data = self.__session.get(flash_var['config_data'])
            xh = XMLHandler()
            xml.sax.parseString(raw_data.text.encode(), xh)
            ret = xh.getDict()
            raw_data = eval(ret['crops'].strip())
            for each in raw_data['crops']:
                self.crop_data[str(each['id'])] = each
            with open(data_version + '.json', 'w') as f:
                json.dump(self.crop_data, f)
            # # re method
            # crop_data_re = eval(re.findall(r'<!\[CDATA\[(.*)]]>', crop_data.text, re.S)[0].replace('\n','').replace('\r',''))

    def get_wishtree(self):
        url = API_addr['Wishtree_info'] + '?g_tk=%d' % self.__g_tk
        farmTime, farmKey, farmKey2 = self.get_farmkey()
        form = {
            'farmTime': farmTime,
            'uIdx': self.__uIdx,
            'uinY': self.__uinY,
            'farmKey2': farmKey2,
            'ownerId': self.__uIdx,
            'farmKey': farmKey,
        }
        response = self.__session.post(url, data=form)
        response = json.loads(response.text)
        self.wishtree = {'prevstar': response['freeStarTime'], 'star': response['starlist']}

    def get_hive(self):
        url = API_addr['Hive_info'] + '?g_tk=%d' % self.__g_tk
        farmTime, farmKey, farmKey2 = self.get_farmkey()
        form = {
            'farmTime': farmTime,
            'uIdx': self.__uIdx,
            'uinY': self.__uinY,
            'farmKey2': farmKey2,
            'ownerId': self.__uIdx,
            'farmKey': farmKey,
        }
        response = self.__session.post(url, data=form)
        response = json.loads(response.text)
        self.hive = {'status': response['status'], 'timestamp': response['stamp']}
        pass

    def get_stat(self):
        response = self.__session.post(API_addr['Farmland_stat'])
        self.stat_data = json.loads(response.text)
        if self.__uIdx is None:
            self.__uIdx = self.stat_data['user']['uId']
        if self.__uinY is None:
            self.__uinY = self.stat_data['user']['uinLogin']
        time.sleep(random.randint(1, 5))
        self.get_wishtree()
        time.sleep(random.randint(1, 5))
        self.get_hive()
        time.sleep(random.randint(1, 5))
        self.format_stat()

    def get_farmkey(self):
        key = ['OPdfqwn^&*w(281flebnd1##roplaq', '(UuqQ=Ze93spP*:s1E/kkGt-:s^|Su']
        farmTime = int(time.time())
        farmKey = hashlib.md5()
        farmKey.update((str(farmTime) + key[0][farmTime % 10:]).encode('utf-8'))
        farmKey2 = hashlib.md5()
        farmKey2.update((str(farmTime) + key[1][farmTime % 10:]).encode('utf-8'))
        return farmTime, farmKey.hexdigest(), farmKey2.hexdigest()

    def get_gtk(self):
        hash_tmp = 5381
        for i in range(len(self.__p_skey)):
            hash_tmp += (hash_tmp << 5) + ord(self.__p_skey[i])
        self.__g_tk = hash_tmp & 0x7fffffff
        return self.__g_tk

    def get_bag(self):
        url = API_addr['Farmland_seed'] + '?mod=repertory&act=getUserSeed&g_tk=%d' % self.__g_tk
        farmTime, farmKey, farmKey2 = self.get_farmkey()
        form = {
            'farmTime': farmTime,
            'uIdx': self.__uIdx,
            'uinY': self.__uinY,
            'farmKey2': farmKey2,
            'farmKey': farmKey,
        }
        response = self.__session.post(url, data=form)
        response = json.loads(response.text)
        self.bag = {}
        for each in response:
            if 'cId' in each.keys():
                self.bag[each['cId']] = each
        pass

    def farm_opt_operation(self, land, operation):
        '''
        除草，除虫，浇水
        :param land: 土地id
        :param operation: 操作名称[clearWeed, spraying, water]
        :return: 1：成功  0：失败
        '''
        farmTime, farmKey, farmKey2 = self.get_farmkey()
        form = {
            'farmTime': farmTime,
            'uIdx': self.__uIdx,
            'uinY': self.__uinY,
            'farmKey2': farmKey2,
            'ownerId': self.__uIdx,
            'place': land,
            'farmKey': farmKey,
        }
        url = API_addr['Farmland_operation'] + '?mod=farmlandstatus&act=' + operation + '&g_tk=%d' % self.__g_tk
        response = self.__session.post(url, data=form)
        response = json.loads(response.text)
        return response['code']

    def farm_plant_operation(self, land, operation, cId=0):
        '''
        翻地，种植
        :param land: 土地id
        :param operation: 操作名称[scarify, harvest, planting]
        :return: 1：成功  0：失败
        '''
        farmTime, farmKey, farmKey2 = self.get_farmkey()
        form = {
            'farmTime': farmTime,
            'uIdx': self.__uIdx,
            'uinY': self.__uinY,
            'farmKey2': farmKey2,
            'ownerId': self.__uIdx,
            'place': land,
            'farmKey': farmKey
        }
        if operation == 'scarify':
            form['cropStatus'] = form['uIdx']
        elif operation == 'planting':
            form['cId'] = cId
        url = API_addr['Farmland_plant'] + '?mod=farmlandstatus&act=' + operation + '&g_tk=%d' % self.__g_tk
        response = self.__session.post(url, data=form)
        response = json.loads(response.text)
        return response['code']

    def wishtree_star(self):
        url = API_addr['Wishtree_operation'] + '?g_tk=%d' % self.__g_tk
        if len(self.wishtree['star']) == 10:
            return 0
        id = random.randint(1, 10)
        while id in self.wishtree['star']:
            id = random.randint(1, 10)
        farmTime, farmKey, farmKey2 = self.get_farmkey()
        form = {
            'farmTime': farmTime,
            'uIdx': self.__uIdx,
            'uinY': self.__uinY,
            'farmKey2': farmKey2,
            'type': 0,
            'id': id,
            'farmKey': farmKey
        }
        response = self.__session.post(url, data=form)
        response = json.loads(response.text)
        if response['code'] == 1:
            self.wishtree['star'].append(id)
        return response['code']

    def hive_harvest(self):
        url = API_addr['Hive_harvest'] + '?g_tk=%d' % self.__g_tk
        farmTime, farmKey, farmKey2 = self.get_farmkey()
        form = {
            'farmTime': farmTime,
            'uIdx': self.__uIdx,
            'uinY': self.__uinY,
            'farmKey2': farmKey2,
            'farmKey': farmKey
        }
        response = self.__session.post(url, data=form)
        response = json.loads(response.text)
        return response['code']

    def hive_work(self):
        url = API_addr['Hive_work'] + '?g_tk=%d' % self.__g_tk
        farmTime, farmKey, farmKey2 = self.get_farmkey()
        form = {
            'farmTime': farmTime,
            'uIdx': self.__uIdx,
            'uinY': self.__uinY,
            'farmKey2': farmKey2,
            'farmKey': farmKey
        }
        response = self.__session.post(url, data=form)
        response = json.loads(response.text)
        return response['code']

    def buy_seed(self, cId):
        url = API_addr['Farmland_buyseed'] + '?mod=repertory&act=buySeed&g_tk=%d' % self.__g_tk
        farmTime, farmKey, farmKey2 = self.get_farmkey()
        form = {
            'farmTime': farmTime,
            'uIdx': self.__uIdx,
            'uinY': self.__uinY,
            'farmKey2': farmKey2,
            'number': 1,
            'cId': cId,
            'farmKey': farmKey
        }
        response = self.__session.post(url, data=form)
        response = json.loads(response.text)
        return response['code']

    def format_stat(self):
        land_remapper = {0: '普通', 1: '红土地', 2: '黑土地', 3: '金土地', 8: '紫金土地', 16: '蓝晶土地', 32: '黑晶土地'}
        landid_remapper = {0: 0, 1: 1, 2: 2, 3: 3, 8: 4, 16: 5, 32: 6}
        pos_remapper = [[0, 3], [0, 2], [0, 1],
                        [1, 3], [1, 2], [1, 1],
                        [2, 3], [2, 2], [2, 1],
                        [3, 3], [3, 2], [3, 1],
                        [4, 3], [4, 2], [4, 1],
                        [5, 3], [5, 2], [5, 1],
                        [0, 0], [1, 0], [2, 0], [3, 0], [4, 0], [5, 0]]
        self.land = [[{} for i in range(4)] for j in range(6)]
        for i in range(min(24, len(self.stat_data['farmlandStatus']))):
            server_data = self.stat_data['farmlandStatus'][i]
            # 土地编号
            self.land[pos_remapper[i][0]][pos_remapper[i][1]]['id'] = i
            # 土地类型
            if server_data['isGoldLand'] == 1:
                self.land[pos_remapper[i][0]][pos_remapper[i][1]]['land'] = land_remapper[3]
                self.land[pos_remapper[i][0]][pos_remapper[i][1]]['landid'] = 3
            else:
                self.land[pos_remapper[i][0]][pos_remapper[i][1]]['land'] = land_remapper[server_data['bitmap']]
                self.land[pos_remapper[i][0]][pos_remapper[i][1]]['landid'] = landid_remapper[server_data['bitmap']]

            if server_data['a'] != 0:
                crop_data_tmp = self.crop_data[str(server_data['a'])]
            else:
                self.land[pos_remapper[i][0]][pos_remapper[i][1]]['name'] = '空地'
                self.land[pos_remapper[i][0]][pos_remapper[i][1]]['statusid'] = server_data['b']
                self.land[pos_remapper[i][0]][pos_remapper[i][1]]['status'] = '空地'
                self.land[pos_remapper[i][0]][pos_remapper[i][1]]['season'] = 0
                self.land[pos_remapper[i][0]][pos_remapper[i][1]]['ttlseason'] = 0
                self.land[pos_remapper[i][0]][pos_remapper[i][1]]['croplvl'] = 0
                self.land[pos_remapper[i][0]][pos_remapper[i][1]]['plant_time'] = 0
                self.land[pos_remapper[i][0]][pos_remapper[i][1]]['ttl_time'] = 0
                self.land[pos_remapper[i][0]][pos_remapper[i][1]]['grass'] = False
                self.land[pos_remapper[i][0]][pos_remapper[i][1]]['insect'] = False
                self.land[pos_remapper[i][0]][pos_remapper[i][1]]['water'] = False
                continue

            # 作物土地等级
            if 'isRed' in crop_data_tmp.keys():
                self.land[pos_remapper[i][0]][pos_remapper[i][1]]['croplvl'] = crop_data_tmp['isRed']
            else:
                self.land[pos_remapper[i][0]][pos_remapper[i][1]]['croplvl'] = 0
            # 作物名称
            self.land[pos_remapper[i][0]][pos_remapper[i][1]]['name'] = crop_data_tmp['name']
            # 作物状态
            self.land[pos_remapper[i][0]][pos_remapper[i][1]]['statusid'] = server_data['b']
            if server_data['b'] == 7:
                self.land[pos_remapper[i][0]][pos_remapper[i][1]]['status'] = '枯萎'
            elif server_data['b'] == 0:
                self.land[pos_remapper[i][0]][pos_remapper[i][1]]['status'] = '空地'
            else:
                try:
                    self.land[pos_remapper[i][0]][pos_remapper[i][1]]['status'] = crop_data_tmp['nextText'].split(',')[
                        server_data['b'] - 1]
                except:
                    self.land[pos_remapper[i][0]][pos_remapper[i][1]]['status'] = '未知错误'
            # 第几季
            self.land[pos_remapper[i][0]][pos_remapper[i][1]]['season'] = server_data['j'] + 1
            # 共几季
            self.land[pos_remapper[i][0]][pos_remapper[i][1]]['ttlseason'] = crop_data_tmp['harvestNum']
            # 成熟时间
            self.land[pos_remapper[i][0]][pos_remapper[i][1]]['plant_time'] = server_data['q']
            self.land[pos_remapper[i][0]][pos_remapper[i][1]]['ttl_time'] = int(crop_data_tmp['cropGrow'].split(',')[4])
            # 是否需要除草
            self.land[pos_remapper[i][0]][pos_remapper[i][1]]['grass'] = server_data['f'] == 1
            # 是否需要除虫
            self.land[pos_remapper[i][0]][pos_remapper[i][1]]['insect'] = server_data['g'] == 1
            # 是否需要浇水
            self.land[pos_remapper[i][0]][pos_remapper[i][1]]['water'] = server_data['h'] == 0
            pass
        pass

    def login(self):
        login_url = 'https://qzone.qq.com/'
        driver = webdriver.Chrome()
        driver.get(login_url)
        while driver.current_url == login_url:
            time.sleep(1 / 60)
        cookies = driver.get_cookies()
        with open('cookies.json', 'w') as f:
            json.dump(cookies, f)
        driver.close()
        jar = requests.cookies.RequestsCookieJar()
        for each in cookies:
            jar.set(each['name'], each['value'], domain=each['domain'], path=each['path'])
            if each['name'] == 'skey':
                self.__p_skey = each['value']
        self.__session.cookies = jar
        pass

    def by_pass_login(self):
        if not os.path.exists('cookies.json'):
            self.login()
            return
        with open('cookies.json', 'r') as f:
            cookies = json.load(f)
        jar = requests.cookies.RequestsCookieJar()
        for each in cookies:
            jar.set(each['name'], each['value'], domain=each['domain'], path=each['path'])
            if each['name'] == 'skey':
                self.__p_skey = each['value']
        self.__session.cookies = jar
        response = self.__session.post(API_addr['Farmland_stat'])
        response = json.loads(response.text)
        if 'errorContent' in response.keys():
            print('需要重新登录')
            self.login()

    def __init__(self):
        self.by_pass_login()
        self.get_gtk()
        self.get_crop_data()
        self.get_bag()


def console_print(bot_obj):
    minium_stamp = 1 << 63
    tb = pt.PrettyTable()
    tb.field_names = ['1', '2', '3', '4', '历史操作']
    land_discount = {0: 1.0, 1: 1.0, 2: 0.8, 3: 0.8, 4: 0.75, 5: 0.72, 6: 0.72}
    all_data = [[] for i in range(29)]
    for row in range(29):
        if row % 5 == 0:
            for col in range(4):
                all_data[row].append('%d%s(第%d/%d季)' % (bot_obj.land[row // 5][col]['id'],
                                                        bot_obj.land[row // 5][col]['name'],
                                                        bot_obj.land[row // 5][col]['season'],
                                                        bot_obj.land[row // 5][col]['ttlseason']))
        elif row % 5 == 1:
            for col in range(4):
                if bot_obj.land[row // 5][col]['statusid'] == 6:
                    all_data[row].append(Fore.YELLOW + '成熟' + Fore.RESET)
                elif bot_obj.land[row // 5][col]['status'] == '枯萎':
                    all_data[row].append(Fore.CYAN + '枯萎' + Fore.RESET)
                elif bot_obj.land[row // 5][col]['status'] == '空地':
                    all_data[row].append(Fore.CYAN + '空地' + Fore.RESET)
                else:
                    all_data[row].append(bot_obj.land[row // 5][col]['status'])
        elif row % 5 == 2:
            for col in range(4):
                now = int(time.time())
                if bot_obj.land[row // 5][col]['croplvl'] < bot_obj.land[row // 5][col]['landid']:
                    mul = land_discount[bot_obj.land[row // 5][col]['landid']]
                else:
                    mul = 1
                remained = (bot_obj.land[row // 5][col]['plant_time'] +
                            bot_obj.land[row // 5][col]['ttl_time'] * mul) - now
                minium_stamp = min(minium_stamp, remained)
                m, s = divmod(max(0, remained), 60)
                h, m = divmod(m, 60)
                all_data[row].append('%02d时%02d分%02d秒成熟' % (h, m, s))
        elif row % 5 == 3:
            for col in range(4):
                op = []
                if bot_obj.land[row // 5][col]['grass']:
                    op.append('除草')
                if bot_obj.land[row // 5][col]['insect']:
                    op.append('除虫')
                if bot_obj.land[row // 5][col]['water']:
                    op.append('浇水')
                all_data[row].append(Fore.RED + '需要' + ','.join(op) + Fore.RESET if op else '无需操作')
        elif row % 5 == 4:
            for col in range(4):
                all_data[row].append(' ')
        if row < len(bot_obj.history):
            all_data[row].append(bot_obj.history[row])
        else:
            all_data[row].append(' ')

    all_data[24][4] = '-------------------------'
    all_data[25][4] = '许愿树状态'
    now = int(time.time())
    diff = bot_obj.wishtree['prevstar'] - now + 8 * 60 * 60
    if diff < 0:
        diff *= -1
        sig = '-'
    else:
        sig = ''
    minium_stamp = min(minium_stamp, diff + 1800)
    m, s = divmod(diff, 60)
    h, m = divmod(m, 60)
    all_data[26][4] = '%s%02d时%02d分%02d秒摘星' % (sig, h, m, s)

    status = ['闲置', '采蜜', '休息']
    need_time = [0, 14400, 5400]
    all_data[27][4] = '蜂巢：%s' % status[bot_obj.hive['status']]
    diff = bot_obj.hive['timestamp'] - now + need_time[bot_obj.hive['status']]
    minium_stamp = min(minium_stamp, diff + 1800)
    if diff < 0:
        diff *= -1
        sig = '-'
    else:
        sig = ''
    m, s = divmod(diff, 60)
    h, m = divmod(m, 60)
    all_data[28][4] = '%s%02d时%02d分%02d秒' % (sig, h, m, s)

    for row in range(29):
        tb.add_row(all_data[row])
    print('')
    print(tb, end = '')
    return minium_stamp


def auto_operation(bot_obj):
    operated = False
    # 许愿树脚本
    now = int(time.time())
    if now > bot_obj.wishtree['prevstar'] + 8 * 60 * 60 + random.randint(5 * 60, 15 * 60):
        print('尝试摘星')
        if bot_obj.wishtree_star():
            print('摘星成功')
            now = datetime.datetime.now().strftime('%H:%M:%S')
            bot_obj.history.insert(0, now + ' 摘星成功')
            operated = True

    # 蜂巢脚本
    now = int(time.time())
    if bot_obj.hive['status'] == 1 and now > bot_obj.hive['timestamp'] + 14400 + random.randint(5 * 60, 15 * 60):
        print('尝试收取蜂蜜')
        if bot_obj.hive_harvest():
            print('蜂蜜收取成功')
            now = datetime.datetime.now().strftime('%H:%M:%S')
            bot_obj.history.insert(0, now + ' 蜂蜜收取成功')
            operated = True
    elif bot_obj.hive['status'] == 2 and now > bot_obj.hive['timestamp'] + 5400 + random.randint(5 * 60, 15 * 60):
        print('尝试放蜂')
        if bot_obj.hive_work():
            print('放蜂成功')
            now = datetime.datetime.now().strftime('%H:%M:%S')
            bot_obj.history.insert(0, now + ' 放蜂成功')
            operated = True

    # 农场本体脚本
    for each_row in bot_obj.land:
        for each_col in each_row:
            now = datetime.datetime.now().strftime('%H:%M:%S')
            if each_col['grass']:
                print('尝试除草')
                if bot_obj.farm_opt_operation(each_col['id'], 'clearWeed') == 1:
                    print('%d号田除草成功' % each_col['id'])
                    bot_obj.history.insert(0, now + ' %d号田除草成功' % each_col['id'])
                    each_col['grass'] = False
                    operated = True
                else:
                    print('%d号田除草失败' % each_col['id'])
                    bot_obj.history.insert(0, now + ' %d号田除草失败' % each_col['id'])
                time.sleep(1)
            if each_col['insect']:
                print('尝试除虫')
                if bot_obj.farm_opt_operation(each_col['id'], 'spraying') == 1:
                    print('%d号田除虫成功' % each_col['id'])
                    bot_obj.history.insert(0, now + ' %d号田除虫成功' % each_col['id'])
                    each_col['insect'] = False
                    operated = True
                else:
                    print('%d号田除虫失败' % each_col['id'])
                    bot_obj.history.insert(0, now + ' %d号田除虫失败' % each_col['id'])
                time.sleep(1)
            if each_col['water']:
                print('尝试浇水')
                if bot_obj.farm_opt_operation(each_col['id'], 'water') == 1:
                    print('%d号田浇水成功' % each_col['id'])
                    bot_obj.history.insert(0, now + ' %d号田除草成功' % each_col['id'])
                    each_col['water'] = False
                    operated = True
                else:
                    print('%d号田浇水失败' % each_col['id'])
                    bot_obj.history.insert(0, now + ' %d号田浇水失败' % each_col['id'])
                time.sleep(1)
            if each_col['statusid'] == 6:
                print('尝试收获')
                if bot_obj.farm_plant_operation(each_col['id'], 'harvest') == 1:
                    print('%d号田收获成功' % each_col['id'])
                    bot_obj.history.insert(0, now + ' %d号田收获成功' % each_col['id'])
                    each_col['season'] += 1
                    operated = True
                time.sleep(1)
            if each_col['status'] == '枯萎' or each_col['season'] > each_col['ttlseason']:
                print('尝试翻地')
                if bot_obj.farm_plant_operation(each_col['id'], 'scarify') == 1:
                    print('%d号田翻地成功' % each_col['id'])
                    bot_obj.history.insert(0, now + ' %d号田翻地成功' % each_col['id'])
                    each_col['status'] = '空地'
                    operated = True
                time.sleep(1)
            if each_col['status'] == '空地':
                continue
                if 0 <= each_col['id'] <= 2:
                    # 荷花玉兰
                    cId = 1060
                elif 3 <= each_col['id'] <= 5:
                    # 月宴
                    cId = 966
                elif 6 <= each_col['id'] <= 8:
                    # 柔紫千红
                    cId = 747
                elif 9 <= each_col['id'] <= 11:
                    # 金桔
                    cId = 74
                elif 12 <= each_col['id'] <= 13:
                    # 栗子
                    cId = 95
                elif 14 <= each_col['id'] <= 15:
                    continue
                    # 牧草
                    cId = 40
                elif 16 <= each_col['id'] <= 17:
                    continue
                    # 牧草
                    cId = 40
                elif 18 <= each_col['id'] <= 19:
                    # 包里有啥种啥，没有买种子
                    cId = -1
                    black_list = [40, 4472]
                    for key, value in bot_obj.bag.items():
                        if key not in black_list:
                            cId = key
                            break
                    if cId == -1:
                        cId = 747
                elif 20 <= each_col['id'] <= 23:
                    # 牧草
                    cId = 40
                else:
                    continue
                has_seed = False
                if cId in bot_obj.bag.keys() and bot_obj.bag[cId]['amount'] > 0:
                    has_seed = True
                if not has_seed:
                    print('尝试购买种子')
                    code = bot_obj.buy_seed(cId)
                    if code == 1:
                        print('购买种子%d成功' % cId)
                        bot_obj.history.insert(0, now + ' 购买种子%d成功' % cId)
                        time.sleep(1)
                if has_seed or (not has_seed and code == 1):
                    print('尝试补种')
                    if bot_obj.farm_plant_operation(each_col['id'], 'planting', cId=cId) == 1:
                        print('%d号田补种成功' % each_col['id'])
                        if has_seed:
                            bot_obj.bag[cId]['amount'] -= 1
                        bot_obj.history.insert(0, now + ' %d号田补种成功' % each_col['id'])
                        operated = True
                time.sleep(1)
            pass
    if operated:
        time.sleep(random.randint(5, 15))
        bot_obj.get_stat()
        bot_obj.format_stat()
    pass


def script():
    bot = Bot()
    # bot.login()
    timer = 0
    while True:
        if timer % 3000 == 0:
            bot.get_stat()
            bot.format_stat()
            console_print(bot)
            auto_operation(bot)
            bot.by_pass_login()
            time.sleep(5)
        else:
            bot.format_stat()
            stamp = console_print(bot)
            if stamp < -600:
                timer = -1
        timer += 1
        time.sleep(1)


def test():
    bot = Bot()
    bot.get_bag()


def run():
    cnt = 0
    while True:
        try:
            if cnt >= 3:
                break
            script()
            cnt = 0
        except Exception as e:
            print(e)
            time.sleep(15)
            cnt += 1


if __name__ == '__main__':
    run()
