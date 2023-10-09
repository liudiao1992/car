
import importlib
import lxml
import requests
import pymysql
from bs4 import BeautifulSoup
import re
import json
import sys
import os
from urllib import parse
import time
import threading
from dbutils.pooled_db import PooledDB

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
pool = PooledDB(
    #使用数据库的模块
    creator=pymysql, 

    #设置最大连接数量     
    maxconnections=32,  

    #设置初始空闲连接数量    
    mincached=10, 

    #连接池中没有空闲连接后设置是否等待，True等待，False不等待
    blocking=True,   
    
    #检查服务是否可用
    ping=0,

    host='127.0.0.1',
    user='root',
    password='root',
    db = 'car',
    port=3306,
)

# HOSTNAME = '127.0.0.1'
# USERNAME = 'root'
# PASSWORD = 'root'
# DATABASE = 'car'

conn =  pool.connection() 
# conn = pymysql.connect(host = HOSTNAME, user=USERNAME, password=PASSWORD, database=DATABASE, charset="utf8")
cur = conn.cursor()


# print cur
ip = ''
ip_time = 0
brandUrl = 'https://car.autohome.com.cn'
seriesUrl = 'https://car.autohome.com.cn/price/series-{}.html'
modelUrl = 'https://car.autohome.com.cn/config/spec/{}.html#pvareaid={}'

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
    
#保存车辆图片
def image_save(series_data):
    for info in series_data:
        brand_id = info[0]
        path = "D:/work/uploads/car/" + str(brand_id)
        if not os.path.exists(path):
            os.mkdir(path)
        series_id = info[1]
        url = 'https://www.autohome.com.cn/'+str(series_id)
        print(url)
        res = requests.get(url)
        if res.status_code == 200:
            res.close()
            # res.encoding = 'gb2312'
        soup = BeautifulSoup(res.text, "lxml")
        main_pic = soup.find(class_='pic-main')
        main_pic1 = soup.find(class_='models_pics')
        if main_pic:   
            main_url = 'http:' + main_pic.find('a').get('href')
        elif main_pic1:
            main_url = 'http:' + main_pic1.find('dt').find('a').get('href')
        else:
            continue
        result = requests.get(main_url)
        if result.status_code == 200:
            result.close()
        parse_url = parse.urlparse(main_url)
        url_path = parse_url.path.split('/')
        img_id = url_path[4][:-5]
        print(img_id)
        
        soup1 = BeautifulSoup(result.text, "lxml")  
        #获取主图
        current_li = soup1.find('li',{'id':'li'+img_id})
        if  not current_li:
            continue
        else:
            current_li_image = current_li.find('img')
            if not current_li_image:
                continue
            else:
                main_image_url = 'http:'+ current_li_image.get('src')
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36'}
                # 调用get_ip函数，获取代理IP
                proxies = get_ip()
                # 每次发送请求换代理IP，获取图片，防止被封
                img_data = requests.get(url=main_image_url, headers=headers, proxies=proxies).content
                # img_data = requests.get(url=main_image_url, headers=headers).content
                # 拼接图片存放地址和名字
                img_path = path+'/'+str(series_id)+'.jpg'
                # 将图片写入指定位置
                with open(img_path, 'wb') as f:
                    f.write(img_data)
                    image_value = 'uploads/car/'+str(brand_id)+'/'+str(series_id)+'.jpg'
                cur.execute("UPDATE car_series SET %s='%s' where series_id = %d" % ('main_image',image_value,series_id))
                conn.commit()
                
                    
                #继续获取其他图片    
                i = 1
                img_list = []
                while i<=5: 
                    current_li = current_li.find_next('li')
                    if not current_li:
                        break
                    else:
                        current_li_image = current_li.find('img')
                        if not current_li_image:
                            break
                        else:
                            img_list.append('http:'+ current_li_image.get('src'))
                    i = i+1
                print(img_list)
                
                key = 1
                other_images = []
                images_value = ''
                for item in img_list:
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36'}
                    # 调用get_ip函数，获取代理IP
                    proxies = get_ip()
                    # 每次发送请求换代理IP，获取图片，防止被封
                    # img_data = requests.get(url=item, headers=headers).content
                    img_data = requests.get(url=item, headers=headers, proxies=proxies).content
                    # 拼接图片存放地址和名字
                    img_path = path+'/'+str(series_id)+'_'+str(key)+'.jpg'
                    # 将图片写入指定位置
                    with open(img_path, 'wb') as f:
                        f.write(img_data)
                        other_image_value = 'uploads/car/'+str(brand_id)+'/'+str(series_id)+'_'+str(key)+'.jpg'
                        other_images.append(other_image_value)
                    key = key + 1
                images_value = ','.join(other_images) 
                cur.execute("UPDATE car_series SET %s='%s' where series_id = %d" % ('other_images',images_value,series_id))
                conn.commit()
    cur.close()
    conn.close()
    
                
                
#获取ip
def get_ip():
    global ip,ip_time
    if time.time() >= ip_time + 60:
        url = "http://v2.api.juliangip.com/dynamic/getips?auto_white=1&num=1&pt=1&result_type=text&split=1&trade_no=1649731001581632&sign=a7f8fdaa211aa60215ebdc87e946b487"
        while 1:
            try:
                r = requests.get(url, timeout=10)
            except:
                continue

            ip = r.text.strip()
            ip_time = time.time()
            if '请求过于频繁' in ip:
                print('IP请求频繁')
                time.sleep(1)
                continue
            break
    print(ip)
    proxies = {
        'https': '%s' % ip
    }
    return proxies       

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


def thread1():
    sql = 'select brand_id,series_id,firm,firmurl,levelname,model,modelurl,brandurl from car_series where id >= 1893 and id<2000'
    cur.execute(sql)
    data = cur.fetchall()
    image_save(data)
    print('线程1处理完成')
    
    
def thread2():
    sql = 'select brand_id,series_id,firm,firmurl,levelname,model,modelurl,brandurl from car_series where id >= 2701 and id<3000'
    cur.execute(sql)
    data = cur.fetchall()
    image_save(data)
    print('线程2处理完成')

def thread3():
    sql = 'select brand_id,series_id,firm,firmurl,levelname,model,modelurl,brandurl from car_series where id >= 3000'
    cur.execute(sql)
    data = cur.fetchall()
    image_save(data)
    print('线程3处理完成')
    

def main():
    # t1 = threading.Thread(target=thread1)
    t2 = threading.Thread(target=thread2)
    # t3 = threading.Thread(target=thread3)
    
    # t1.start()
    t2.start()
    # t3.start()
    
    
    
    #车辆品牌
    # result = get_brand()
    #根据品牌获取对应车系数据并保存数据库
    # obtain_series(result,type='series')
    #车系数据未保存至数据库
    #车系颜色
    # obtain_series(result,type='color')
    #具体车款
    # obtain_series(result,type='model_type')
    
    #车系数据保存至数据库后从数据库获取车系数据
    # sql = 'select brand_id,series_id,firm,firmurl,levelname,model,modelurl,brandurl from car_series where id >= 598'
    # cur.execute(sql)
    # data = cur.fetchall()
    #具体车款
    # model_type_handle(data)
    #车系颜色
    # color_save(data)
    # 车辆图片
    # image_save(data)
    

if '__main__' == __name__:
    main()