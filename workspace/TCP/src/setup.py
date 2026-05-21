from setuptools import find_packages, setup

# 🌟 修正一：套件名稱必須是 section3，對應 src/ 底下的資料夾名稱
package_name = 'TCP_section3'

setup(
    name=package_name,
    version='0.0.0',
    # find_packages() 會自動幫你掃描並包含 'section3' 資料夾
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='root',
    maintainer_email='a2a45a789@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            # 🌟 修正二：嚴格對齊「內層資料夾.主檔名:入口函數」
            'state = TCP_section3.main:main',
        ],
    },
)