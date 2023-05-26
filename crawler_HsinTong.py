import urllib.request as req
import bs4
import json
import csv

##################################################################################################
####### 抓出各標題內文中的聯絡人、電話 #######
def getContact(url):
    request = req.Request(url, headers = {
        "User-Agent" : "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1 Edg/110.0.0.0"
    })
    with req.urlopen(request) as response:
        data = response.read().decode("utf-8")
    root = bs4.BeautifulSoup(data, "lxml")
    
    title_box = root.find("div", class_ = "data_midlle_news_box01") ## 先找到目標區塊
    contact_info = title_box.find("dd") ## 找到區塊內的聯絡資料
    
    ##########################
    ##  這裡需要額外使用另一個文本分析套件
    ##  因為<dd>標籤裡面的文字都包在一起，我們需要挑出特定的部分
    contact_text = contact_info.get_text()
    
    import re
    
    ##撈出聯絡人
    contact_person_match = re.search("聯絡人：(...)\s+", contact_text)  ## 聯絡人的名字是二~三個字的
    if contact_person_match:
        contact_person = contact_person_match.group(1)
    else:
        contact_person_match = re.search("聯絡人：(.....)\s+", contact_text) ## 名字包含職稱
        if contact_person_match:
            contact_person = contact_person_match.group(1)
        else:
            contact_person_match = re.search("聯絡人：(.......)\s+", contact_text) ## 名字包含職稱(更長)
            if contact_person_match:
                contact_person = contact_person_match.group(1)
            else:
                contact_person = "no match"
    
    ##撈出電話
    phone_match = re.search("電話：(.+?)\s+電子信箱", contact_text)  ## 電話格式的括號是半形
    if phone_match:
        phone = phone_match.group(1)
    else:
        phone_match = re.search("電話：（.+?）\s+電子信箱", contact_text)  ## 電話格式的括號是全形
        if phone_match:
            phone = phone_match.group(1)
        else:
            phone = "no match"
    ##########################
        
    return contact_person, phone

##################################################################################################
####### 抓出新聞日期、標題、公告單位 #######
def getData(url):
    ##  建立一個 Request物件，附加 Request Headers 的資訊（模擬使用者）
    request = req.Request(url, headers = {
        "User-Agent" : "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1 Edg/110.0.0.0"
    })

    ##  透過request發出請求
    with req.urlopen(request) as response:
        data = response.read().decode("utf-8")
    root = bs4.BeautifulSoup(data, "lxml")

    ## 把時間、標題、發布單位抓出來
    middle_news = root.find("div", class_ = "data_midlle_news")  ## class = "data_midlle_news" 網站原本就拼錯了
    news_titles = middle_news.find("div").find_all("a")          ## "找到所有 middle_news底下的<div><a></a></div>標籤"
    news_timestamp = middle_news.find("div").find_all("td", align = "center")
    news_issued = middle_news.find("div").find_all("td", align = "left")
    
    date_temp = []
    title_temp = []
    unit_temp = []
    url_temp = []
    for title in news_titles:
        title_temp.append(title.string.strip())
        link = title["href"]
        if link:   ## 如果標題連結存在，抓出href串成完整網址
            contentURL = "https://www.edu.tw/" + link
            url_temp.append(contentURL)
    for date in news_timestamp:
        date_temp.append(date.string.strip())
    for unit in news_issued:
        unit_temp.append(unit.string.strip())
    print("本頁日期、標題、單位、url爬取完成")
    
    nextPage = root.find("a", string = "下一頁")  ## 找到下一頁的內容
    
    return nextPage["href"], date_temp, title_temp, unit_temp, url_temp ## get(url) 會回傳下一頁的網址

##################################################################################################
####### 合併五個list並輸出成csv、json #######
def output(date_list, title_list, unit_list, name_list, tel_list):
    combined_list = list(zip(date_list, title_list, unit_list, name_list, tel_list))

    ## 寫進csv
    with open("news.csv", "w", newline = "", encoding = "utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["發布日期", "新聞標題", "公告單位", "聯絡人", "聯絡電話"])
        writer.writerows(combined_list)

    

    # 寫進json
    json_list = []
    for i in range(len(date_list)):
        data = {
            "date": date_list[i],
            "title": title_list[i],
            "unit": unit_list[i],
            "author": {
                "name": name_list[i],
                "tel": tel_list[i]
            }
        }
        json_data = json.dumps(data, ensure_ascii = False)
        json_list.append(json_data)

    # 將 json_list 中的資料寫入檔案
    with open("news.json", "w", encoding = "utf-8") as f:
        f.write("[\n")
        f.write(",\n".join(json_list))
        f.write("\n]")

    ## 清空陣列
    date_list.clear()
    title_list.clear()
    unit_list.clear()
    name_list.clear()
    tel_list.clear()
    
##################################################################################################
####### 將 getContact()、getData() 整合 #######
def crawl_data(num_records, target_unit):
    # 創建五個data list
    date_list = []
    title_list = []
    unit_list = []
    name_list = []
    tel_list = []
    
    url = "https://www.edu.tw/News.aspx?n=9E7AC85F1954DDA8"
    ## 先抓時間、標題、公告單位就好
    nextPage, date_temp, title_temp, unit_temp, url_temp = getData(url)
    count = 0
    while True:
        for i in range(len(date_temp)):
            ## 搜尋特定公告單位
            if target_unit != unit_temp[i] and target_unit != "all":
                continue ## 不符合就跳走
            ## 符合就將資料加進list
            date_list.append(date_temp[i])
            title_list.append(title_temp[i])
            unit_list.append(unit_temp[i])
            contact_person, phone = getContact(url_temp[i])  ## 符合的單位要額外用getContact() 去抓他的聯絡人及電話
            name_list.append(contact_person.strip())
            tel_list.append(phone.strip())

            count += 1
            print("第" + str(count) + "筆資料爬取完成")
            
            if count == num_records:
                print("爬蟲完畢")
                return date_list, title_list, unit_list, name_list, tel_list
        # 如果沒有下一頁，就跳出迴圈
        if nextPage is None:
            break
        else:
            url = "https://www.edu.tw/" + nextPage
            nextPage, date_temp, title_temp, unit_temp, url_temp = getData(url)  ## 抓下一頁
    print("爬蟲完畢")
    return date_list, title_list, unit_list, name_list, tel_list

##################################################################################################
####### 輸入系統 #######
while True:
    num_records = int(input("需要爬取多少筆資料？（請輸入1~200000之間的數）"))
    if 0 < num_records and num_records < 200000:
        break
    else:
        print("輸入的筆數需介於1~200000，請重新輸入。")

    
unit_list = ['高等教育司',
             '學生事務及特殊教育司',
             '資訊及科技教育司',
             '人事處',
             '國教署',
             '師資培育及藝術教育司',
             '國際及兩岸教育司',
             '終身教育司',
             '技術及職業教育司',
             '綜合規劃司',
             '青年署',
             '教育部',
             '體育署', 
             'all']  ## 另外弄一個小爬蟲抓出近1000筆新聞的發布單位
while True:
    flag = False
    target_unit = input("輸入要搜尋的單位：")
    for unit in unit_list:
        if target_unit == unit:
            flag = True
            break
    if flag:
        break
    else:
        print("輸入的單位不符合要求，請重新輸入。")

##################################################################################################
####### 輸出 #######
print("資料爬取中...請稍後")
date_list, title_list, unit_list, name_list, tel_list = crawl_data(num_records, target_unit)
print("請至此程式的資料夾中確認檔案（news.csv及news.json）")
output(date_list, title_list, unit_list, name_list, tel_list)

##################################################################################################