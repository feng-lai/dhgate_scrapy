from flask import Flask, render_template, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
import re
import pandas as pd
import requests
import json
from flask import Flask, request, jsonify
from urllib.parse import urljoin



app = Flask(__name__)

def fix_json_string(s):
    # 尝试修复 JSON 字符串
    try:
        # 替换单引号为双引号
        s = s.replace("'", '"')
        # 移除末尾的错误字符
        s = re.sub(r'[^\x00-\x7F]+', '', s)  # 移除非ASCII字符
        return json.loads(s)
    except json.JSONDecodeError:
        return []  # 如果解析失败，返回空列表
    
def process_page(parent_url,category):
    print("访问父页面:", parent_url)
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

    # 访问父页面
    driver.get(parent_url)

    # 初始化产品信息列表
    product_info_list = []

    try:
        # 等待页面元素加载
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".pro-title a")))
        print("父页面加载完成")

        # 定位所有产品链接
        product_links = driver.find_elements(By.CSS_SELECTOR, "p.pro-title a")
        if product_links:
            print(f"找到 {len(product_links)} 个子页面链接")

            # 提取子页面链接
            subpage_urls = [link.get_attribute('href') for link in product_links if link.get_attribute('href')]
            print(f"提取到 {len(subpage_urls)} 个子页面链接")
        else:
            # 如果没有找到任何产品链接，将父页面链接加入子页面链接列表
            subpage_urls = [parent_url]
            print(f"未找到子页面链接，将父页面链接 {parent_url} 加入子页面链接列表")

    except TimeoutException:
        # 如果父页面加载超时，直接将父页面作为子页面处理
        subpage_urls = [parent_url]
        print("父页面加载超时，将父页面链接加入子页面链接列表")

    finally:
        # 逐个访问子页面链接
        for index, subpage_url in enumerate(subpage_urls):
            print(f"\n开始处理第 {index + 1} 个子页面: {subpage_url}")
            try:
                # 打开子页面
                driver.get(subpage_url)
                print("子页面开始加载")
                
                # 等待子页面元素加载
                try:
                    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "title")))
                    print("子页面标题加载完成")
                except TimeoutException:
                    print("子页面加载超时")
                    continue

                # 提取子页面信息
                raw_title = driver.title
                # 分割标题并取"From"前的部分
                parts = raw_title.split("From")
                title = parts[0].strip() if len(parts) > 1 else raw_title
                print(f"提取到标题: {title}")
                
                # 提取描述和描述图片
                description_images = []
                description = ""
                try:
                    description_div = driver.find_element(By.CSS_SELECTOR, ".div-description.div-wrap")
                    description_list = description_div.find_elements(By.CSS_SELECTOR, "ul.list-paddingleft-2 > li")
                    for item in description_list:
                        description += item.text + "\n"
                    # 提取描述中的图片链接
                    description_images += [img.get_attribute('src') for img in description_div.find_elements(By.TAG_NAME, "img")]
                    print("提取到描述")
                except NoSuchElementException:
                    try:
                        # 尝试提取 #imglist 内的描述
                        imglist_div = driver.find_element(By.CSS_SELECTOR, "#imglist")
                        description_elements = imglist_div.find_elements(By.TAG_NAME, "p")
                        for element in description_elements:
                            description += element.text + "\n"
                        # 提取 #imglist 内的图片链接
                        description_images += [img.get_attribute('src') for img in imglist_div.find_elements(By.TAG_NAME, "img")]
                        print("提取到 #imglist 内的描述")
                    except NoSuchElementException:
                        # 尝试提取备用描述和图片
                        try:
                            backup_description_div = driver.find_element(By.CSS_SELECTOR, ".prodDescNav_descTabItem__gW6mA .prodDesc_descrptionCon__5wXkd .prodDesc_decHtml__YL_2o")
                            description_elements = backup_description_div.find_elements(By.TAG_NAME, "p")
                            for element in description_elements:
                                description += element.text + "\n"
                            # 提取备用描述中的图片链接
                            description_images += [img.get_attribute('src') for img in backup_description_div.find_elements(By.TAG_NAME, "img")]
                            print("提取到备用描述")
                        except NoSuchElementException:
                            print("备用描述也未找到")
                
                try:
                    keywords = driver.find_element(By.XPATH, "//meta[@name='keywords']").get_attribute("content")
                    print("提取到关键词")
                except NoSuchElementException:
                    keywords = "No keywords found"
                
                # 提取价格
                try:
                    price_element = driver.find_element(By.CSS_SELECTOR, ".col-price.j-col-price")
                    price_text = price_element.text.strip().replace("\n", " ")
                    # 使用正则表达式提取最低价格
                    match = re.search(r'\$(\d+\.\d+)', price_text)
                    if match:
                        price = match.group(1)
                        print("提取到价格:", price)
                    else:
                        price = "No price found"
                except NoSuchElementException:
                    try:
                        price_element = driver.find_element(By.CSS_SELECTOR, "b.productPrice_price__LcDwB.productPrice_blackPrice__XEETh")
                        price_text = price_element.text.strip().replace("\n", " ")
                        match = re.search(r'\$(\d+\.\d+)', price_text)
                        if match:
                            price = match.group(1)
                            print("提取到备用价格:", price)
                        else:
                            price = "No price found"
                    except NoSuchElementException:
                        price = "No price found"

                # 提取选项内容
                options = []
                try:
                    # 尝试提取主要选项
                    option_elements = driver.find_elements(By.CSS_SELECTOR, "li.j-list-sku span label img")
                    for img in option_elements:
                        alt_text = img.get_attribute('alt')
                        title_text = img.get_attribute('title')
                        option = alt_text or title_text  # 使用alt文本，如果没有则使用title文本
                        options.append(option)
                    print("提取到选项:", options)
                except NoSuchElementException:
                    # 如果主要选项不存在，尝试提取备用选项
                    try:
                        # 尝试展开下拉选择框并提取所有选项
                        def get_all_options(driver):
                            try:
                                select_box = driver.find_element(By.CSS_SELECTOR, ".ant-select")
                                actions = ActionChains(driver)
                                actions.move_to_element(select_box).click(select_box).perform()
                                WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".ant-select-dropdown")))
                                options = driver.find_elements(By.CSS_SELECTOR, ".ant-select-dropdown-menu-item")
                                return [option.text for option in options]
                            except NoSuchElementException:
                                return []
                        
                        all_options = get_all_options(driver)
                        if all_options:
                            options.extend(all_options)
                            print("提取到备用选项:", options)
                        else:
                            print("没有找到备用选项栏，跳过")
                    except NoSuchElementException:
                        options = []
                        print("备用选项栏未找到，跳过")
                        
                # 提取图片URL
                images = ["None"] * 8
                for i in range(8):
                    try:
                        # 尝试提取图片URL
                        bimg_inner = driver.find_element(By.CSS_SELECTOR, f'.bimg-inner[data-index="{i}"]')
                        img_url = bimg_inner.get_attribute('data-imgurl') if bimg_inner.get_attribute('data-imgurl') else None
                        if not img_url:
                            img_element = bimg_inner.find_element(By.CSS_SELECTOR, 'img.j-prod-img')
                            img_url = img_element.get_attribute('src') if img_element else None
                        images[i] = img_url if img_url else "None"
                        print(f"提取到图片 {i + 1}: {img_url}")
                    except NoSuchElementException:
                        # 如果主要图片不存在，尝试提取备用图片
                        try:
                            image_element = driver.find_element(By.CSS_SELECTOR, f'.masterMap_smallMapList__JTkBX li[spm-index="{i + 1}"] img')
                            images[i] = image_element.get_attribute('src')
                            print(f"提取到备用图片 {i + 1}")
                        except NoSuchElementException:
                            # 如果备用图片也不存在，保留None
                            pass
                
                # 将信息添加到列表
                product_info_list.append({
                    'Title': title,
                    'Description': description,
                    'Description Images': description_images,
                    'Keywords': keywords,
                    
                    'Price': price,
                    'Options': options,
                    'img1': images[0],
                    'img2': images[1],
                    'img3': images[2],
                    'img4': images[3],
                    'img5': images[4],
                    'img6': images[5],
                    'img7': images[6],
                    'img8': images[7]
                })

            except TimeoutException:
                print(f"处理第 {index + 1} 个子页面超时")
            except NoSuchElementException as e:
                print(f"处理第 {index + 1} 个子页面时发生NoSuchElementException: {e}")
            except StaleElementReferenceException as e:
                print(f"处理第 {index + 1} 个子页面时发生StaleElementReferenceException: {e}")

    # 退出WebDriver
    driver.quit()

    # 将产品信息列表转换为 DataFrame
    df = pd.DataFrame(product_info_list)

    # 检查是否有产品信息需要保存
    if not df.empty:
        try:
            # 定义 CSV 文件的路径
            file_path = 'product_info.csv'
            # 将 DataFrame 保存到 CSV 文件，不包含索引，确保编码为 utf-8
            df.to_csv(file_path, index=False, encoding='utf-8')
            print(f"{category}信息已成功保存到 '{file_path}'")
        except Exception as e:
            print(f"保存{category}信息到 CSV 文件时发生错误: {e}")
    else:
        print("没有{category}信息可以保存。")    

    return product_info_list

def scrape_product_info(parent_url,category):
    print("访问父页面:", parent_url)

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    
    # 访问父页面
    driver.get(parent_url)

    # 等待页面元素加载
    try:
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".grid-product__link")))
        print("父页面加载完成")
    except TimeoutException:
        print("Timed out waiting for page to load")
        driver.quit()
        return {"error": "父页面加载超时"}

    # 定位所有产品链接
    product_links = driver.find_elements(By.CSS_SELECTOR, ".grid-product__link")
    print(f"找到 {len(product_links)} 个子页面链接")

    # 提取父页面的基础路径
    base_url = parent_url.split('?')[0]  # 移除查询参数

    # 提取子页面链接
    subpage_urls = [urljoin(base_url, link.get_attribute('href')) for link in product_links if link.get_attribute('href')]

    print(f"提取到 {len(subpage_urls)} 个子页面链接")

    # 初始化产品信息列表
    product_info_list = []

    # 逐个访问子页面链接
    for index, subpage_url in enumerate(subpage_urls):
        print(f"\n开始处理第 {index + 1} 个子页面: {subpage_url}")
        try:
            # 打开子页面
            driver.get(subpage_url)
            print("子页面开始加载")
            
            # 等待子页面元素加载
            try:
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "title")))
                print("子页面标题加载完成")
            except TimeoutException:
                print("子页面加载超时")
                continue

            # 提取子页面信息
            title = driver.find_element(By.CSS_SELECTOR, "h1.product-single__title").text.strip()
            print(f"提取到标题: {title}")
            
            description = ""
            try:
                description_div = driver.find_element(By.CSS_SELECTOR, ".easyslider-text")
                description = description_div.get_attribute('outerHTML')  # 直接获取outerHTML
                print("提取到描述HTML")
            except NoSuchElementException:
                pass
            
            keywords = "No keywords found"
            try:
                keywords = driver.find_element(By.XPATH, "//meta[@name='keywords']").get_attribute("content")
                print("提取到关键词")
            except NoSuchElementException:
                pass
            
            # 提取价格
            price = "0"
            try:
                price_element = driver.find_element(By.CSS_SELECTOR, "span.product__price.on-sale")
                price = ''.join(filter(str.isdigit, price_element.text.strip()))
                print("提取到价格:", price)
            except NoSuchElementException:
                pass
            
            specifications = {}
            try:
                attributes = driver.find_elements(By.CSS_SELECTOR, ".attrul li")
                for attribute in attributes:
                    key = attribute.find_element(By.TAG_NAME, "strong").text.strip()
                    value = attribute.find_element(By.CSS_SELECTOR, ".des-wrap").text.strip()
                    specifications[key] = value
                print("提取到规格")
            except NoSuchElementException:
                pass
            
            # 提取选项信息
            options = []
            try:
                option_fields = driver.find_elements(By.CSS_SELECTOR, "fieldset.variant-input-wrap")
                for field in option_fields:
                    # 获取字段名称
                    option_inputs = field.find_elements(By.CSS_SELECTOR, ".variant-input")
                    for option_input in option_inputs:
                        option_value = option_input.get_attribute("data-value")
                        if option_value:
                            options.append(option_value)
                print("提取到选项信息:", options)
            except NoSuchElementException as e:
                print(f"在提取选项信息时发生NoSuchElementException: {e}")
            except Exception as e:
                print(f"在提取选项信息时发生异常: {e}")

            # 提取图片URL
            images = ["None"] * 8  # 初始化图片列表
            try:
                # 尝试从 .product__thumb 提取图片URL
                thumb_items = driver.find_elements(By.CSS_SELECTOR, ".product__thumb")
                for i, item in enumerate(thumb_items):
                    if i >= 8:  # 只提取前8张图片
                        break
                    img_url = item.get_attribute('data-zoom')
                    if not img_url:  # 如果data-zoom属性不存在，尝试提取srcset
                        img_url = item.find_element(By.TAG_NAME, 'img').get_attribute('srcset').split(' ')[0]
                    # 转换为绝对路径，去除前缀的 //，并去掉 ?v= 后面的部分
                    img_url = 'https:' + img_url.split('?v=')[0]
                    images[i] = img_url if img_url else "None"
                    print(f"提取到图片 {i + 1}: {img_url}")
            except NoSuchElementException:
                pass
            
            # 如果 .product__thumb 中未找到图片，则尝试从 .main-image-selector 中提取
            if all(img == "None" for img in images):
                try:
                    main_image_selector = driver.find_element(By.CSS_SELECTOR, ".main-image-selector.photo-zoom-link")
                    img_url = main_image_selector.get_attribute('data-zoom-size')
                    img_url = 'https:' + img_url.split('?v=')[0]  # 转换为绝对路径，并去掉 ?v= 后面的部分
                    images[0] = img_url
                    print(f"提取到图片 1: {img_url}")
                except NoSuchElementException as e:
                    print(f"在提取主要图片时发生NoSuchElementException: {e}")
                except Exception as e:
                    print(f"在提取主要图片时发生异常: {e}")

            # 提取评论信息
            name_list = []
            content_list = []
            try:
                reviews = driver.find_elements(By.CSS_SELECTOR, ".stamped-review")
                for review in reviews:
                    name = review.find_element(By.CSS_SELECTOR, ".author").text.strip()
                    content = review.find_element(By.CSS_SELECTOR, ".stamped-review-content-body").text.strip()
                    name_list.append(name)
                    content_list.append(content)
                print("提取到评论信息:", name_list, content_list)
            except NoSuchElementException as e:
                print(f"在提取评论信息时发生NoSuchElementException: {e}")
            except Exception as e:
                print(f"在提取评论信息时发生异常: {e}")

            # 将信息添加到列表
            product_info_list.append({
                'Title': title,
                'Description': description,
                'Keywords': keywords,
                'Specifications': specifications,
                'Price': price,
                'Options': options,
                'img1': images[0],
                'img2': images[1],
                'img3': images[2],
                'img4': images[3],
                'img5': images[4],
                'img6': images[5],
                'img7': images[6],
                'img8': images[7],
                'Name': name_list,
                'Content': content_list
            })

        except TimeoutException:
            print(f"处理第 {index + 1} 个子页面超时")
        except NoSuchElementException as e:
            print(f"处理第 {index + 1} 个子页面时发生NoSuchElementException: {e}")
        except StaleElementReferenceException as e:
            print(f"处理第 {index + 1} 个子页面时发生StaleElementReferenceException: {e}")

    # 退出WebDriver
    driver.quit()

    # 创建包含产品信息的DataFrame
    df = pd.DataFrame(product_info_list)
        # 检查是否有产品信息需要保存
    if not df.empty:
        try:
            # 定义 CSV 文件的路径
            file_path = 'product_info.csv'
            # 将 DataFrame 保存到 CSV 文件，不包含索引，确保编码为 utf-8
            df.to_csv(file_path, index=False, encoding='utf-8')
            print(f"{category}信息已成功保存到 '{file_path}'")
        except Exception as e:
            print(f"保存{category}信息到 CSV 文件时发生错误: {e}")
    else:
        print("没有{category}信息可以保存。")    

    return product_info_list



@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        bag_url = request.form.get('bag_url')
        jewelry_url = request.form.get('jewelry_url')

        if bag_url:  # 检查bag_url是否非空
            product_info_list = process_page(bag_url, '包装袋')
            return render_template('results.html', product_info=product_info_list)
        elif jewelry_url:  # 检查jewelry_url是否非空
            product_info_list = scrape_product_info(jewelry_url, '首饰')
            return render_template('results.html', product_info=product_info_list)
        else:
            return jsonify({"error": "请至少提供一个有效的网址。"})
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    results = []  # 存储上传结果
    cat_id = int(request.json.get('cat_id', 57))  # 获取cat_id，默认为57
    s_id = int(request.json.get('s_id', 307))  # 获取s_id，默认为307

    # 读取CSV文件
    df = pd.read_csv('product_info.csv')

    url = 'https://img.maiiepay.com/pro_save'
    headers = {'Content-Type': 'application/json'}

    for index, row in df.iterrows():
        description = row['Description']

        # 检查是否存在'Description Images'列
        if 'Description Images' in df.columns and pd.notna(row['Description Images']):
            img_links = fix_json_string(row['Description Images'])

            # 构建描述字符串，并加入图片标签
            html_description = f"<p>{description}</p><br><br>"
            for img_link in img_links:
                html_description += f"<img src='{img_link}' alt='产品图片'><br><br>"
        else:
            # 如果不存在'Description Images'或为空，则直接使用原始描述
            html_description = f"<p>{description}</p>"

        # 构建数据字典
        data = {
            "price": str(row['Price']),
            "itm_name": row['Title'],
            "itm_dsc": html_description,  # 使用包含图片的描述或原始描述
            "cat_id": cat_id,
            "s_id": s_id,
            "eva": [],  # 假设没有评价数据
        }

        # 添加图片链接
        for i in range(1, 9):
            img_key = f"img{i}"
            if img_key in row and not pd.isnull(row[img_key]):
                img_link = str(row[img_key])
                data[img_key] = img_link
                print(f"第 {index + 1} 行数据 - 图片 {i} 上传链接: {img_link}")
                
        # 处理Options列
        if pd.notnull(row['Options']):
            try:
                options = json.loads(row['Options'].replace("'", '"'))  # 确保使用双引号
                if options:  # 检查options列表是否不为空
                    data['attr'] = [{"name": "Options", "value": [{"v": option} for option in options]}]
                else:
                    # 如果options列表为空，则不添加attr字段
                    print(f"第 {index + 1} 行Options列表为空，不上传attr字段")
            except json.JSONDecodeError:
                print(f"第 {index + 1} 行Options列不是有效的JSON格式")
                # 如果解析失败，不上传attr字段

        eva_list = []
        for i in range(1, 41):  # 假设最多可能有40条评论
            eva_name = row.get(f"eva_name{i}")
            eva_content = row.get(f"eva_content{i}")
            if pd.notnull(eva_name) and pd.notnull(eva_content):
                eva_list.append({"name": eva_name, "content": eva_content, "level": 5})

        # 如果存在评论，则添加到数据字典中
        if eva_list:
            data['eva'] = eva_list

        # 发送POST请求
        response = requests.post(url, data=json.dumps(data), headers=headers)

        if response.status_code == 200:
            result = f"第 {index + 1} 行数据上传成功:<pre>{response.json()}</pre>"
        else:
            result = f"第 {index + 1} 行数据上传失败:<pre>{response.json()}</pre>"

        results.append(result)

    return jsonify(results)  # 返回所有行的结果

if __name__ == '__main__':
    app.run(debug=True)