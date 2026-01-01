#!/usr/bin/env python3
"""
视频人声消除工具
使用AI模型分离人声和背景音乐，去除人声后重新合成视频
"""

import sys
import logging
import subprocess
import shutil
from pathlib import Path
import argparse

# 创建日志记录器
logger = logging.getLogger(__name__)


class VocalRemover:
    def __init__(self, method='demucs', temp_dir=None):
        """
        初始化人声消除器
        
        Args:
            method: 使用的分离方法 ('demucs' 或 'spleeter')
            temp_dir: 临时文件目录（可选，默认为 output/temp_audio）
        """
        self.method = method
        if temp_dir is None:
            self.temp_dir = Path("output") / "temp_audio"
        else:
            self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
    def check_dependencies(self):
        """检查必要的依赖是否已安装，缺失时自动安装"""
        logger.info("检查依赖...")
        
        # 检查FFmpeg
        try:
            subprocess.run(['ffmpeg', '-version'], 
                         capture_output=True, check=True)
            logger.info("✓ FFmpeg 已安装")
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("✗ 错误: 未找到 FFmpeg")
            logger.error("  请从 https://ffmpeg.org/download.html 下载并安装 FFmpeg")
            logger.error("  或使用: winget install ffmpeg")
            return False
        
        # 检查Python包，缺失时自动安装
        if self.method == 'demucs':
            try:
                import demucs
                logger.info("✓ Demucs 已安装")
            except ImportError:
                logger.warning("✗ 未安装 Demucs，正在自动安装...")
                try:
                    import pip
                    subprocess.run([sys.executable, '-m', 'pip', 'install', 'demucs'], 
                                 check=True)
                    logger.info("✓ Demucs 安装成功")
                except Exception as e:
                    logger.error(f"✗ 自动安装失败: {e}")
                    logger.error("  请手动运行: pip install demucs")
                    return False
            
            # 注意：使用 --mp3 参数时不需要 torchcodec，所以跳过检查
            # torchcodec 只在保存 WAV 格式时需要，但我们使用 MP3 格式输出
        elif self.method == 'spleeter':
            try:
                import spleeter
                logger.info("✓ Spleeter 已安装")
            except ImportError:
                logger.warning("✗ 未安装 Spleeter，正在自动安装...")
                try:
                    subprocess.run([sys.executable, '-m', 'pip', 'install', 'spleeter'], 
                                 check=True)
                    logger.info("✓ Spleeter 安装成功")
                except Exception as e:
                    logger.error(f"✗ 自动安装失败: {e}")
                    logger.error("  请手动运行: pip install spleeter")
                    return False
        
        return True
    
    def extract_audio(self, video_path, output_audio_path):
        """从视频中提取音频"""
        logger.info(f"从视频提取音频: {video_path}")
        cmd = [
            'ffmpeg', '-i', str(video_path),
            '-vn', '-acodec', 'libmp3lame',
            '-ar', '44100', '-ac', '2',
            '-y', str(output_audio_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info(f"✓ 音频已提取到: {output_audio_path}")
    
    def separate_with_demucs(self, audio_path, output_dir):
        """使用Demucs分离人声和伴奏"""
        logger.info("使用 Demucs 分离音频...")
        logger.info("这可能需要几分钟时间，请耐心等待...")
        
        cmd = [
            'python', '-m', 'demucs.separate',
            '--two-stems', 'vocals',
            '--out', str(output_dir),
            '--mp3',  # 使用MP3格式输出，避免torchcodec依赖问题
            str(audio_path)
        ]
        
        try:
            subprocess.run(cmd, check=True)
            logger.info("✓ 音频分离完成")
            
            # Demucs输出结构: separated/htdemucs/文件名/vocals.mp3 和 no_vocals.mp3 (使用--mp3时)
            audio_name = Path(audio_path).stem
            separated_dir = output_dir / 'htdemucs' / audio_name
            # 优先查找mp3格式（使用--mp3参数时），如果不存在则查找wav格式
            vocals_path = separated_dir / 'vocals.mp3'
            no_vocals_path = separated_dir / 'no_vocals.mp3'
            if not vocals_path.exists():
                vocals_path = separated_dir / 'vocals.wav'
            if not no_vocals_path.exists():
                no_vocals_path = separated_dir / 'no_vocals.wav'
            
            return vocals_path, no_vocals_path
        except subprocess.CalledProcessError as e:
            logger.error(f"✗ Demucs分离失败: {e}")
            return None, None
    
    def separate_with_spleeter(self, audio_path, output_dir):
        """使用Spleeter分离人声和伴奏"""
        logger.info("使用 Spleeter 分离音频...")
        logger.info("这可能需要几分钟时间，请耐心等待...")
        
        cmd = [
            'spleeter', 'separate',
            '-i', str(audio_path),
            '-p', 'spleeter:2stems',
            '-o', str(output_dir)
        ]
        
        try:
            subprocess.run(cmd, check=True)
            logger.info("✓ 音频分离完成")
            
            # Spleeter输出结构: output_dir/文件名/accompaniment.wav 和 vocals.wav
            audio_name = Path(audio_path).stem
            separated_dir = output_dir / audio_name
            vocals_path = separated_dir / 'vocals.wav'
            accompaniment_path = separated_dir / 'accompaniment.wav'
            
            return vocals_path, accompaniment_path
        except subprocess.CalledProcessError as e:
            logger.error(f"✗ Spleeter分离失败: {e}")
            return None, None
    
    def merge_audio_video(self, video_path, audio_path, output_path):
        """将处理后的音频合并回视频"""
        logger.info("合并音频和视频...")
        cmd = [
            'ffmpeg', '-i', str(video_path),
            '-i', str(audio_path),
            '-c:v', 'copy',  # 复制视频流，不重新编码
            '-c:a', 'aac',   # 音频编码为AAC
            '-map', '0:v:0',  # 使用第一个输入的视频流
            '-map', '1:a:0',  # 使用第二个输入的音频流
            '-shortest',      # 以最短的流为准
            '-y', str(output_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info(f"✓ 视频已保存到: {output_path}")
    
    def process_video(self, video_path, output_path=None, keep_vocals=False):
        """
        处理视频，去除人声
        
        Args:
            video_path: 输入视频路径
            output_path: 输出视频路径（可选）
            keep_vocals: 如果为True，保留人声去除背景音乐；如果为False，去除人声保留背景音乐
        """
        video_path = Path(video_path)
        
        if not video_path.exists():
            logger.error(f"✗ 错误: 文件不存在: {video_path}")
            return False
        
        if output_path is None:
            output_path = video_path.parent / f"{video_path.stem}_no_vocals{video_path.suffix}"
        else:
            output_path = Path(output_path)
        
        # 检查依赖
        if not self.check_dependencies():
            return False
        
        try:
            # 1. 提取音频
            audio_path = self.temp_dir / f"{video_path.stem}.mp3"
            self.extract_audio(video_path, audio_path)
            
            # 2. 分离人声和伴奏
            if self.method == 'demucs':
                vocals_path, background_path = self.separate_with_demucs(
                    audio_path, self.temp_dir
                )
            else:  # spleeter
                vocals_path, background_path = self.separate_with_spleeter(
                    audio_path, self.temp_dir
                )
            
            if not background_path or not background_path.exists():
                logger.error("✗ 错误: 音频分离失败")
                return False
            
            # 3. 选择要使用的音频（去除人声=使用背景音乐）
            # 验证文件是否存在
            if not vocals_path.exists():
                logger.error(f"✗ 错误: 人声文件不存在: {vocals_path}")
                return False
            
            if keep_vocals:
                final_audio = vocals_path
                logger.info("保留人声，去除背景音乐")
                logger.info(f"  使用文件: {vocals_path.name}")
            else:
                final_audio = background_path
                logger.info("去除人声，保留背景音乐")
                logger.info(f"  使用文件: {background_path.name}")
            
            # 4. 合并音频和视频
            self.merge_audio_video(video_path, final_audio, output_path)
            
            logger.info("✓ 处理完成！")
            logger.info(f"  输出文件: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"✗ 处理过程中出错: {e}", exc_info=True)
            return False
        finally:
            # 清理临时文件（可选，注释掉以保留临时文件用于调试）
            # self.cleanup()
            pass
    
    def cleanup(self):
        """清理临时文件"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            logger.info("✓ 已清理临时文件")


def main():
    parser = argparse.ArgumentParser(
        description='去除视频中的人声，保留背景音乐',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 去除人声，保留背景音乐
  python remove_vocals.py video.mp4
  
  # 指定输出文件
  python remove_vocals.py video.mp4 -o output.mp4
  
  # 使用Spleeter方法
  python remove_vocals.py video.mp4 --method spleeter
  
  # 保留人声，去除背景音乐
  python remove_vocals.py video.mp4 --keep-vocals
        """
    )
    
    parser.add_argument('video', help='输入视频文件路径')
    parser.add_argument('-o', '--output', help='输出视频文件路径（可选）')
    parser.add_argument('-m', '--method', 
                       choices=['demucs', 'spleeter'],
                       default='demucs',
                       help='使用的分离方法 (默认: demucs)')
    parser.add_argument('--keep-vocals', action='store_true',
                       help='保留人声，去除背景音乐（默认是去除人声保留背景音乐）')
    parser.add_argument('--cleanup', action='store_true',
                       help='处理完成后清理临时文件')
    
    args = parser.parse_args()
    
    remover = VocalRemover(method=args.method)
    success = remover.process_video(
        args.video, 
        args.output, 
        keep_vocals=args.keep_vocals
    )
    
    if args.cleanup:
        remover.cleanup()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()


