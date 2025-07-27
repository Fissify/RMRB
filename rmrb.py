import requests
import bs4
import os
import datetime
import time
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

# 定义RUL函数
def fetchUrl(url):
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36',
    }  # 伪装headers
    r = requests.get(url, headers=headers)
    r.raise_for_status()  # 查看请求
    r.encoding = r.apparent_encoding
    return r.text

# 获取页面信息
def getPageList(year, month, day):
    url = f'http://paper.people.com.cn/rmrb/pc/layout/{year}{month}/{day}/node_01.html'  # 人民日报的网址构造是年份+月份+日期+版面
    html = fetchUrl(url)
    bsobj = bs4.BeautifulSoup(html, 'html.parser')  # 使用bs4解析网页
    temp = bsobj.find('div', attrs={'id': 'pageList'})  # 查看网页元素
    if temp:
        pageList = temp.ul.find_all('div', attrs={'class': 'right_title-name'})
    else:
        pageList = bsobj.find('div', attrs={'class': 'swiper-container'}).find_all('div', attrs={'class': 'swiper-slide'})
    linkList = []
    for page in pageList:
        link = page.a["href"]
        url = f'http://paper.people.com.cn/rmrb/pc/layout/{year}{month}/{day}/{link}'
        linkList.append(url)
    return linkList

# 获取标题列表
def getTitleList(year, month, day, pageUrl):
    html = fetchUrl(pageUrl)
    bsobj = bs4.BeautifulSoup(html, 'html.parser')
    temp = bsobj.find('div', attrs={'id': 'titleList'})  # 查看标题元素
    if temp:
        titleList = temp.ul.find_all('li')
    else:
        titleList = bsobj.find('ul', attrs={'class': 'news-list'}).find_all('li')
    linkList = []
    for title in titleList:
        tempList = title.find_all('a')
        for temp in tempList:
            link = temp["href"]
            if 'content' in link:
                url = f'http://paper.people.com.cn/rmrb/pc/content/{year}{month}/{day}/{link}'
                linkList.append(url)
    return linkList

# 获取文章内容
def getContent(html):
    bsobj = bs4.BeautifulSoup(html, 'html.parser')
    try:
        title = bsobj.h3.text + '\n' + bsobj.h1.text + '\n' + bsobj.h2.text + '\n'
    except:
        title = ''
    pList = bsobj.find('div', attrs={'id': 'ozoom'}).find_all('p')
    content = ''
    for p in pList:
        content += p.text + '\n'
    return title + content  # 将标题和正文组合

# 保存文件
def saveFile(content, path, filename):
    if not os.path.exists(path):
        os.makedirs(path)
    full_path = os.path.join(path, filename)
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"已保存文件：{full_path}")

# 下载单篇文章
def download_article(year, month, day, pageNo, titleNo, url, destdir):
    try:
        html = fetchUrl(url)
        content = getContent(html)
        path = os.path.join(destdir, f'{year}{month}{day}')
        fileName = f'{year}{month}{day}-{str(pageNo).zfill(2)}-{str(titleNo).zfill(2)}.txt'
        saveFile(content, path, fileName)
    except Exception as e:
        print(f"\n下载失败: {url} 错误: {e}")

#下载整个页面文章
def download_rmrb(year, month, day, destdir):
    pageList = getPageList(year, month, day)
    with ThreadPoolExecutor(max_workers=10) as executor:  # 使用线程池创建10个线程来并行下载（可自行修改）
        futures = []
        for pageNo, page in enumerate(pageList, start=1):
            try:
                titleList = getTitleList(year, month, day, page)
                for titleNo, url in enumerate(titleList, start=1):
                    futures.append(executor.submit(download_article, year, month, day, pageNo, titleNo, url, destdir))
            except Exception as e:
                print(f"页面错误：{page} 错误信息：{e}")
        for _ in tqdm(as_completed(futures), total=len(futures), desc=f"{year}-{month}-{day} 下载进度"):  # 加载进度条进行监督
            pass

# 日期生成器
def gen_dates(b_date, days):
    day = datetime.timedelta(days=1)
    for i in range(days):
        yield b_date + day * i

# 获取日期列表
def get_date_list(beginDate, endDate):
    start = datetime.datetime.strptime(beginDate, "%Y%m%d")
    end = datetime.datetime.strptime(endDate, "%Y%m%d")
    return [d for d in gen_dates(start, (end - start).days + 1)]

# 主程序入口
if __name__ == '__main__':
    print("欢迎使用人民日报爬虫（支持进度条与多线程）")
    beginDate = input('请输入开始日期（如 20250101）: ')
    endDate = input('请输入结束日期（如 20250102）: ')
    destdir = input("请输入保存路径（如 D:/data/rmrb/ ）: ").strip()
    data = get_date_list(beginDate, endDate)  #生成日期列表

    for d in data:
        year = str(d.year)
        month = str(d.month).zfill(2)
        day = str(d.day).zfill(2)
        download_rmrb(year, month, day, destdir)  # 根据日期调用函数进行数据爬取
        print(f"爬取完成：{year}{month}{day}\n")
        time.sleep(5)  # 每次爬取完成后，休眠5秒以避免过于频繁地请求

    input("所有数据爬取完成！按回车键关闭程序")