"""
路径管理模块
用于统一管理项目中的文件路径，确保所有文件操作使用相对于项目根目录的标准路径
"""

import os
import sys

class PathManager:
    """
    路径管理类，提供获取项目各种文件路径的方法
    所有文件应存放在项目根目录的相应文件夹中，而非源代码目录
    """
    
    @staticmethod
    def get_project_root():
        """
        获取项目根目录的绝对路径
        支持开发环境和打包后的生产环境
        """
        if getattr(sys, 'frozen', False):
            # 打包后的环境：使用可执行文件所在目录
            return os.path.dirname(sys.executable)
        else:
            # 开发环境：使用源代码路径
            current_file = os.path.abspath(__file__)
            if 'src' in current_file.split(os.path.sep):
                # 从utils目录上升三级到项目根目录
                return os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
            else:
                # 直接从项目根目录调用
                return os.path.dirname(os.path.dirname(current_file))
    
    @staticmethod
    def get_data_path(filename=None):
        """
        获取数据文件路径
        
        Args:
            filename: 可选，数据文件名
            
        Returns:
            如果提供filename，返回完整的文件路径
            否则返回data目录路径
        """
        data_dir = os.path.join(PathManager.get_project_root(), 'data')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
        
        if filename:
            return os.path.join(data_dir, filename)
        return data_dir
    
    @staticmethod
    def get_experiments_path(filename=None):
        """
        获取实验文件路径
        
        Args:
            filename: 可选，实验文件名
            
        Returns:
            如果提供filename，返回完整的文件路径
            否则返回experiments目录路径
        """
        exp_dir = os.path.join(PathManager.get_project_root(), 'experiments')
        if not os.path.exists(exp_dir):
            os.makedirs(exp_dir, exist_ok=True)
            
        if filename:
            return os.path.join(exp_dir, filename)
        return exp_dir
    
    @staticmethod
    def get_config_path(filename=None):
        """
        获取配置文件路径
        
        Args:
            filename: 可选，配置文件名
            
        Returns:
            如果提供filename，返回完整的文件路径
            否则返回configs目录路径
        """
        config_dir = os.path.join(PathManager.get_project_root(), 'configs')
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
            
        if filename:
            return os.path.join(config_dir, filename)
        return config_dir
    
    @staticmethod
    def get_logs_path(filename=None):
        """
        获取日志文件路径
        
        Args:
            filename: 可选，日志文件名
            
        Returns:
            如果提供filename，返回完整的文件路径
            否则返回logs目录路径
        """
        logs_dir = os.path.join(PathManager.get_project_root(), 'logs')
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir, exist_ok=True)
            
        if filename:
            return os.path.join(logs_dir, filename)
        return logs_dir
    
    @staticmethod
    def get_resources_path(filename=None):
        """
        获取资源文件路径
        
        Args:
            filename: 可选，资源文件名
            
        Returns:
            如果提供filename，返回完整的文件路径
            否则返回resources目录路径
        """
        resources_dir = os.path.join(PathManager.get_project_root(), 'resources')
        if not os.path.exists(resources_dir):
            os.makedirs(resources_dir, exist_ok=True)
            
        if filename:
            return os.path.join(resources_dir, filename)
        return resources_dir
    
    @staticmethod
    def get_exports_path(filename=None):
        """
        获取导出文件路径
        
        Args:
            filename: 可选，导出文件名
            
        Returns:
            如果提供filename，返回完整的文件路径
            否则返回exports目录路径
        """
        exports_dir = os.path.join(PathManager.get_project_root(), 'exports')
        if not os.path.exists(exports_dir):
            os.makedirs(exports_dir, exist_ok=True)
            
        if filename:
            return os.path.join(exports_dir, filename)
        return exports_dir
    
    @staticmethod
    def get_styles_path(filename=None):
        """
        获取样式文件路径
        
        Args:
            filename: 可选，样式文件名
            
        Returns:
            如果提供filename，返回完整的文件路径
            否则返回styles目录路径
        """
        styles_dir = os.path.join(PathManager.get_project_root(), 'resources', 'styles')
        if not os.path.exists(styles_dir):
            os.makedirs(styles_dir, exist_ok=True)
            
        if filename:
            return os.path.join(styles_dir, filename)
        return styles_dir
    
    @staticmethod
    def ensure_directory_exists(directory_path):
        """
        确保目录存在，如果不存在则创建
        
        Args:
            directory_path: 目录路径
        """
        if not os.path.exists(directory_path):
            os.makedirs(directory_path, exist_ok=True)
            
    @staticmethod
    def ensure_file_directory_exists(file_path):
        """
        确保文件所在目录存在，如果不存在则创建
        
        Args:
            file_path: 文件路径
        """
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
    
    @staticmethod
    def get_flame_temp_path(filename=None):
        """
        获取火焰分析临时文件路径
        
        Args:
            filename: 可选，文件名
            
        Returns:
            如果提供filename，返回完整的文件路径
            否则返回temp_captures目录路径
        """
        temp_dir = os.path.join(PathManager.get_data_path(), 'temp_captures')
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir, exist_ok=True)
            
        if filename:
            return os.path.join(temp_dir, filename)
        return temp_dir
    
    @staticmethod
    def get_flame_results_path(filename=None):
        """
        获取火焰分析结果路径
        
        Args:
            filename: 可选，文件名
            
        Returns:
            如果提供filename，返回完整的文件路径
            否则返回flame_results目录路径
        """
        results_dir = os.path.join(PathManager.get_data_path(), 'flame_results')
        if not os.path.exists(results_dir):
            os.makedirs(results_dir, exist_ok=True)
            
        if filename:
            return os.path.join(results_dir, filename)
        return results_dir
    
    @staticmethod
    def get_max_flame_images_path(filename=None):
        """
        获取最大火焰图像保存路径
        
        Args:
            filename: 可选，文件名
            
        Returns:
            如果提供filename，返回完整的文件路径
            否则返回max_flame_images目录路径
        """
        max_flame_dir = os.path.join(PathManager.get_data_path(), 'max_flame_images')
        if not os.path.exists(max_flame_dir):
            os.makedirs(max_flame_dir, exist_ok=True)
            
        if filename:
            return os.path.join(max_flame_dir, filename)
        return max_flame_dir
    
    @staticmethod
    def initialize_directories():
        """
        初始化所有必需的目录
        在应用启动时调用，确保所有目录结构就绪
        """
        # 基础目录
        PathManager.get_data_path()
        # PathManager.get_experiments_path()
        PathManager.get_config_path()
        PathManager.get_logs_path()
        PathManager.get_resources_path()
        # PathManager.get_exports_path()
        
        # 火焰分析目录
        PathManager.get_flame_temp_path()
        PathManager.get_flame_results_path()
        PathManager.get_max_flame_images_path()


# 单元测试
if __name__ == "__main__":
    print(f"项目根目录: {PathManager.get_project_root()}")
    print(f"数据目录: {PathManager.get_data_path()}")
    print(f"实验目录: {PathManager.get_experiments_path()}")
    print(f"配置目录: {PathManager.get_config_path()}")
    print(f"日志目录: {PathManager.get_logs_path()}")
    print(f"资源目录: {PathManager.get_resources_path()}")
    print(f"样式目录: {PathManager.get_styles_path()}")
    print(f"导出目录: {PathManager.get_exports_path()}")
    
    # 火焰分析目录
    print(f"火焰临时目录: {PathManager.get_flame_temp_path()}")
    print(f"火焰结果目录: {PathManager.get_flame_results_path()}")
    print(f"最大火焰图像目录: {PathManager.get_max_flame_images_path()}")
    
    # 测试特定文件路径
    print(f"数据库文件: {PathManager.get_data_path('experiments.db')}")
    print(f"配置文件: {PathManager.get_config_path('exp_settings.config')}")
    print(f"日志文件: {PathManager.get_logs_path('app.log')}")

    print(f"气氛控制程序配置文件: {PathManager.get_config_path('gas_programs')}")
    print(f"温度控制程序配置文件: {PathManager.get_config_path('temp_programs')}")

    # project_root = str(Path(__file__).resolve().parents[2])
    #
    # # 配置文件路径
    # config_path = os.path.join(project_root, "configs", "comm_config.json")