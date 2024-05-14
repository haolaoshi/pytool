import requests  
import json  
from bs4 import BeautifulSoup  
  
def get_github_top_starred_repos(count=100):  
    url = "https://api.github.com/search/repositories?q=stars:>1&sort=stars&order=desc&per_page={}".format(count)  
    headers = {  
        "Accept": "application/vnd.github.v3+json",  
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"  
    }  
      
    repos = []  
    response = requests.get(url, headers=headers)  
    if response.status_code == 200:  
        data = response.json()  
        repos.extend(data["items"])  
      
    return repos  
  
from bs4 import BeautifulSoup  
  
def create_html_page(repos):  
    html_template = """  
    <!DOCTYPE html>  
    <html lang="en">  
    <head>  
        <meta charset="UTF-8">  
        <title>Top GitHub Starred Repositories</title>  
        <style>  
            body { font-family: Arial, sans-serif; }  
            table { width: 100%; border-collapse: collapse; }  
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }  
            th { background-color: #f2f2f2; }
        </style>
    </head>
    <body>
        <table>
            <th>Rank</th>  
                <th>Repository</th>  
                <th>Language</th>  
                <th>Description</th>  
                <th>Link</th>  
            </tr>  
            {% for repo in repos %}  
            <tr>  
                <td>{{ loop.index }}</td>  
                <td><a href="{{ repo.html_url }}">{{ repo.name }}</a></td>  
                <td>{{ repo.language or 'N/A' }}</td>  
                <td>{{ repo.description or 'N/A' }}</td>  
                <td><a href="{{ repo.homepage or repo.html_url }}">Link</a></td>  
            </tr>  
            {% endfor %}  
        </table>  
    </body>  
    </html>  
    """  
  
    # 使用 Jinja2 渲染模板  
    from jinja2 import Template  
    template = Template(html_template)  
    rendered_html = template.render(repos=repos)   
    save_to_html_file(rendered_html) 
  
def save_to_html_file(html_content, filename='top_starred_repos.html'):  
    with open(filename, 'w', encoding='utf-8') as file:  
        file.write(html_content)  
    print
 
# 获取前100个最受欢迎的仓库  
repos = get_github_top_starred_repos(100) 
create_html_page(repos)      
print("HTML文件已保存到当前目录：top_starred_repos.html")