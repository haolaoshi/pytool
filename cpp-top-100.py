import requests  
  
# GitHub API endpoint for searching repositories  
SEARCH_ENDPOINT = "https://api.github.com/search/repositories"  
  
# Function to fetch data from GitHub API  
def fetch_data(query, page=1, per_page=100):  
    headers = {  
        "Accept": "application/vnd.github.v3+json",  
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"  
    }  
    params = {  
        "q": query,  
        "page": page,  
        "per_page": per_page,  
        "sort": "stars",  
        "order": "desc"  
    }  
    response = requests.get(SEARCH_ENDPOINT, headers=headers, params=params)  
    if response.status_code == 200:  
        return response.json()  
    else:  
        print(f"Error fetching data: {response.status_code}")  
        return None  
  
# Generate HTML table rows from repository data  
def generate_html_rows(repositories):  
    rows = ""  
    for index, repo in enumerate(repositories[:100], start=1):  
        name = repo.get("name", "N/A")  
        description = repo.get("description", "N/A")  
        if description is not None:  
            description = description.replace('"', '&quot;')  # Escape double quotes for HTML 
        else:
            description =  name 
        cpp_version = repo.get("topics", [])  
        cpp_version = next((topic for topic in cpp_version if "c++" in topic.lower()), "N/A")  
        html_url = repo.get("html_url", "N/A")  
        font_family = "'Helvetica Neue', Helvetica, Arial, sans-serif" 
        row = f"""  
        <tr>  
            <td>{index}</td>  
            <td><a href="{html_url}">{name}</a></td>  
            <td>{description}</td>  
            <td>{cpp_version}</td>  
            <td><a href="{html_url}">Link</a></td>  
        </tr>  
        """  
        rows += row  
    return rows  
  
def main():  
    query = "language:C++ stars:>0"  
    repositories = []  
    page = 1  
  
    # Fetch data in pages until we have 100 repositories or exhaust the API limit  
    while len(repositories) < 100 and page <= 10:  # GitHub API has a limit of 10 pages for unauthenticated requests  
        results = fetch_data(query, page=page, per_page=100)  
        if results:  
            repositories.extend(results.get("items", []))  
            page += 1  
  
    # Print repository information to the console  
    for rep in repositories:  
        print(rep['language'], rep['html_url'], rep['name'], rep['description'])  
  
    from jinja2 import Template  
    template = Template(html_template)  
    rendered_html = template.render(repos=repositories)  
  
    # Write HTML content to a file  
    with open("top_cpp_repos.html", "w", encoding="utf-8") as file:  
        file.write(rendered_html)  
  
    print("HTML file has been saved with the top 100 C++ repositories!")  
  
# HTML template  
html_template = """  
<!DOCTYPE html>  
<html lang="en">  
<head>  
    <meta charset="UTF-8">  
    <title>Top 100 C++ Repositories on GitHub</title>  
    <style>  
        body { font-family: Arial, sans-serif; }  
        table { width: 100%; border-collapse: collapse; }  
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }  
        th { background-color: #f2f2f2; }  
    </style>  
</head>  
<body>  
    <table>  
        <tr>
            <th>Project Name</th>  
            <th>About Description</th>  
            <th>Star Counts</th>  
            <th>Create At</th>
        </tr>  
        {% for repo in repos %}  
        <tr>  
            <td><a href="{{repo['html_url']}}">{{repo['name']}}</a></td>  
            <td>{{repo['description']}}</td>  
            <td>{{repo['stargazers_count']}}</td>     
            <td>{{repo['created_at']}}</td>  
        </tr>  
        {% endfor %}  
    </table>  
</body>  
</html>
"""  
  
# Define the fetch_data function here or import it from an appropriate module  
# ...  
  
# Call the main function  
if __name__ == "__main__":  
    main()