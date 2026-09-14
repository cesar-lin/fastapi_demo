# 根目录放 conftest.py 的作用是：pytest 导入它时会将项目根目录加入 sys.path，
# 使测试文件可以 `import app...`
