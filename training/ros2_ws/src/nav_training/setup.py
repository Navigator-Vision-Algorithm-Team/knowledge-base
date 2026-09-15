from glob import glob

from setuptools import find_packages, setup


setup(
    name='nav_training',
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/nav_training']),
        ('share/nav_training', ['package.xml', 'LICENSE']),
        ('share/nav_training/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Navigation training maintainers',
    maintainer_email='maintainers@example.invalid',
    description='Isolated ROS 2 teaching nodes, ideal motion and bounded Actions',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={'console_scripts': [
        'sequence_publisher = nav_training.sequence:publisher_main',
        'sequence_subscriber = nav_training.sequence:subscriber_main',
        'ideal_model = nav_training.ideal_model:main',
        'fibonacci_server = nav_training.fibonacci_server:main',
        'fibonacci_client = nav_training.fibonacci_client:main',
    ]},
)
