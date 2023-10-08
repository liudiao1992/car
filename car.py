# encoding:utf-8
# ------------------------------------------------
#    作用：抓取汽车之家车型库
#    日期：2018-03-25
#    作者：呆呆
# ------------------------------------------------


import importlib
import lxml
import requests
import pymysql
from bs4 import BeautifulSoup
import re
import json
import sys

import config_default

configs = config_default.configs

# print configs['full_type_name']['name']

# print configs

# exit()

# print configs.items()

# for key,values in configs.items():
#     print values['name']
# exit
# print 123
# exit()

# importlib.reload(sys)

# sys.setdefaultencoding('utf-8')

HOSTNAME = '127.0.0.1'
USERNAME = 'root'
PASSWORD = 'root'
DATABASE = 'car'

conn = pymysql.connect(host = HOSTNAME, user=USERNAME, password=PASSWORD, database=DATABASE, charset="utf8")
cur = conn.cursor()


# print cur

brandUrl = 'https://car.autohome.com.cn'
seriesUrl = 'https://car.autohome.com.cn/price/series-{}.html'
modelUrl = 'https://car.autohome.com.cn/config/spec/{}.html#pvareaid={}'

# BeautifulSoup用法
'''
soup = BeautifulSoup("<html>data</html>","lxml")
soup = BeautifulSoup('<b name="test" class="boldest">Extremely bold</b>','lxml')
tag = soup.b
# print tag
# print soup.prettify()
# print soup.body
# print type(soup.b)
print soup.name
print soup.b.attrs
print soup.b['class']
print soup.string

print soup.b
print soup.b.string
print type(soup.b.string)

print soup.find_all('b')
soup.find_all(["a", "b"])
soup.find_all("a", limit=2)
soup.find_all(id='link2')

soup.find_all(href=re.compile("elsie"))
soup.find_all("a", class_="sister")
soup.find_all(href=re.compile("elsie"), id='link1')

soup.html.find_all("title")
soup.find_all('b')

print soup.select('#link1')
print soup.select('title')
print soup.select('p #link1')
print soup.select("head > title")
print soup.select('a[class="sister"]')
print soup.select('.sister')

html = ''
soup = BeautifulSoup(html, 'lxml')
print type(soup.select('title'))
print soup.select('title')[0].get_text()

for tag in soup.find_all(re.compile("^b")):
    print(tag.name)

for title in soup.select('title'):
    print title.get_text()
'''

def get_brand():
    res = requests.get('https://car.autohome.com.cn/AsLeftMenu/As_LeftListNew.ashx?typeId=1%20&brandId=0%20&fctId=0%20&seriesId=0')
    # print res
    if res.status_code == 200:
        res.close()
        soup = BeautifulSoup(res.text, 'lxml')

        # for letter in soup.find_all(class_="cartree-letter"):
        #     print letter.get_text()

        data = []
        for letter in soup.select(".cartree-letter"):
            # print args.get("href")
            for li in letter.find_next():
                brand_id = li.get("id")[1:]
                args = li.find("a")
                
                sub_arg = (letter.get_text(),args['href'],re.findall(u'.*\(', args.get_text())[0].replace("(",""),re.findall(u"\d+\.?\d*", args.find("em").get_text())[0],brand_id)
                data.append(sub_arg)


        # 保存所有汽车品牌 
        # cur.executemany('INSERT INTO car_brand (firstletter,linkurl,name,carnum,brand_id) values(%s,%s,%s,%s,%s)', data)
        # conn.commit()
        
        # cur.close()
        # conn.close()

        return data

def obtain_series(data,type):

    host = 'https://car.autohome.com.cn'
    # print(data)
    
    for info in data:
        brand_id = info[4]
        # print("obtain_series_url:"+host + info[1])
        res = requests.get(host+info[1])
        if res.status_code == 200:
            res.close()
        # res.encoding = 'gb2312'
        soup = BeautifulSoup(res.text, "lxml")
        # print(soup.title)

        level_name = ''
        for series in soup.select('div[class="carbradn-cont fn-clear"] dl'):
            series_data = []
            firm = series.find('dt').get_text()
            firm_url = series.find('dt').find('a').get('href')


            for level in series.select("dd div"):
                if level.attrs['class'][0] == 'list-dl-text':
                    level_name = level.find_previous().get_text()[:-1]
                    for model in level.select("a"):

                        model_name = model.get_text()
                        model_url = model.get("href")
                        series_id = re.findall("series-(\d+)[\.|-]",model_url)[0]

                        series_data.append((brand_id,series_id,firm, firm_url, level_name, model_name, model_url, res.url))
            
            if type == 'series':
                try:
                    series_save(series_data)
                except Exception as e:
                    pass
            elif type == 'color':
                try:
                    color_save(series_data)
                except Exception as e:
                    pass
            elif type == 'model_type':
                try:
                    model_type_handle(series_data)
                except Exception as e:
                    pass
            else:
                print("处理方式错误，程序退出")
                exit
                
    print("保存车辆数据完成")
    exit       
    # cur.close()
    # conn.close()
    
#保存车系数据   
def series_save(series_data):
    print(series_data)         
    cur.executemany('INSERT INTO car_series (brand_id,series_id,firm,firmurl,levelname,model,modelurl,brandurl) values(%s,%s,%s,%s,%s,%s,%s,%s)', series_data)
    conn.commit()
    
    
# 保存车系颜色      
def color_save(series_data): 
    for info in series_data:
        color_data = []
        series_id = str(info[1])
        url = 'https://www.autohome.com.cn/'+series_id
        res = requests.get(url)
        if res.status_code == 200:
            res.close()
            # res.encoding = 'gb2312'
        soup = BeautifulSoup(res.text, "lxml")
        for colors in soup.select('div[class="information-pic"] div[class="athm-carcolor__inner"] a div[class="athm-carcolor__tip"]'):
            color = colors.get_text()
            color_data.append((series_id, color))
            
        for colors_more in soup.select('div[class="athm-carcolor__inner-more"] a div[class="athm-carcolor__tip"]'):
            color_more = colors_more.get_text()
            color_data.append((series_id, color_more))
        print(color_data)
        cur.executemany('INSERT INTO car_color (series_id,color) values(%s,%s)', color_data)
        conn.commit()
    


#保存车款信息      
def model_type_handle(series_data):         
    for info in series_data:
        series_id = info[1]
        
        try:
            result = obtain_model(series_id)
            model_type_save(result,series_id)
        except Exception as e:
            pass


def obtain_model(series_id):
    url = 'https://car.m.autohome.com.cn/ashx/car/GetModelConfigNew.ashx?seriesId={}'
    request_model = requests.get(url.format(series_id))
    print(request_model.url)

    if request_model.status_code == 200:
        model_json = request_model.json()
        request_model.close()
        # print(model_json['config'])
        year_items = model_json

        dict_model = dict()
        args = []
        model_count = 0

        for param in ['config','param']:

            for year_item in year_items[param]:

                for chile_item in year_item[param+'items']:

                    # print(chile_item)
                    valueName = chile_item['name']
                    valueItems = chile_item['valueitems']
                    # print(valueName,valueItems)

                    for key,values in configs.items():

                        
                        if valueName == values['name']:
                            enName = key
                            break
                        else:
                            enName = None

                    for spec_item in valueItems:
                        # print(spec_item)
                        model_count = model_count + 1

                        spec_id = spec_item['specid']
                        spec_name = spec_item['value']

                        # spec_name = spec_name
                        if(enName != None):
                            addtwodimdict(dict_model,spec_id,enName,spec_name)
                        # if(enName == 'seat_numer'):
                        #     print(enName)
                            
                        #     print("seat_numer:"+dict_model)
                        #     exit()
                        # print("共{}条，名称{}，值{}".format(model_count,spec_id,spec_name))

                    # print valueItems
        # print dict_model
        return dict_model

#具体车款存储
def model_type_save(data,series_id):
    # print(data)
    values = []
    item_key = []
    pleis = []
    car_name = ''
    car_values = ''
    
    for key,item in data.items():
        if len(item_key) == 0:
            item_key = item.keys()
            for i in item_key:
                pleis.append('%s')
            car_name = ",".join(item_key)
            
        item_value = []
        for k,it in item.items():
            if(it == '-' or it == '●'):
                item_value.append(0)
            else:
                item_value.append(it)
        #车系id
        item_value.append(series_id)
        # print(len(item_value))
        values.append(tuple(item_value))
        
        # values.append(tuple(item.values()))

    #车系id
    pleis.append('%s') 
    car_values = ",".join(pleis)
    if car_name:
        car_name = car_name+',series_id'
        # str = 'INSERT INTO car_model_type('+car_name+') values('+car_values+')'
        # print("sql:"+str)
        cur.executemany('INSERT INTO car_model_type ('+car_name+') values ('+car_values+')', values)
        conn.commit()
    

    # cur.close()
    # conn.close()

#add 2d dict
def addtwodimdict(thedict, key_a, key_b, val):
    if key_a in thedict:
        thedict[key_a].update({key_b: val})
    else:
        thedict.update({key_a:{key_b: val}})


def main():
    
    sql = 'select brand_id,series_id,firm,firmurl,levelname,model,modelurl,brandurl from car_series'
    cur.execute(sql)
    data = cur.fetchall()
    model_type_handle(data)
    # color_save(data)
    # result = get_brand()
    #车系数据
    # obtain_series(result,type='series')
    #车系颜色
    # obtain_series(result,type='color')
    #具体车款
    # obtain_series(result,type='model_type')


if '__main__' == __name__:
    main()