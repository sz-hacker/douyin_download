#!/usr/bin/env python3
"""
视频文字提取工具
支持多种方式从视频中提取文字：
1. 提取嵌入字幕（软字幕）
2. OCR识别画面文字（硬字幕）
3. 语音转文字（ASR）
"""

import os
import sys
import logging
import subprocess
from pathlib import Path
import argparse

# 创建日志记录器
logger = logging.getLogger(__name__)


class VideoTextExtractor:
    def __init__(self, temp_dir=None):
        """
        初始化视频文字提取器
        
        Args:
            temp_dir: 临时文件目录（可选，默认为 output/temp_text）
        """
        if temp_dir is None:
            self.temp_dir = Path("output") / "temp_text"
        else:
            self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def check_dependencies(self):
        """检查必要的依赖"""
        logger.info("检查依赖...")
        
        # 检查FFmpeg
        try:
            subprocess.run(['ffmpeg', '-version'], 
                         capture_output=True, check=True)
            logger.info("✓ FFmpeg 已安装")
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("✗ 错误: 未找到 FFmpeg")
            logger.error("  请从 https://ffmpeg.org/download.html 下载并安装 FFmpeg")
            return False
        
        return True
    
    def extract_embedded_subtitles(self, video_path, output_path=None):
        """
        提取视频中嵌入的字幕轨道（软字幕）
        
        Args:
            video_path: 视频文件路径
            output_path: 输出字幕文件路径（可选，默认输出SRT格式）
        """
        video_path = Path(video_path)
        if not video_path.exists():
            logger.error(f"✗ 错误: 文件不存在: {video_path}")
            return False
        
        logger.info(f"提取嵌入字幕: {video_path}")
        
        # 使用ffmpeg列出所有字幕流
        cmd = [
            'ffmpeg', '-i', str(video_path),
            '-map', '0:s:0?',  # 映射第一个字幕流
            '-c:s', 'srt',     # 转换为SRT格式
            '-y'
        ]
        
        if output_path is None:
            output_path = video_path.parent / f"{video_path.stem}.srt"
        else:
            output_path = Path(output_path)
        
        cmd.append(str(output_path))
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if output_path.exists() and output_path.stat().st_size > 0:
                logger.info(f"✓ 字幕已提取到: {output_path}")
                return True
            else:
                logger.warning("✗ 未找到嵌入字幕轨道")
                return False
        except Exception as e:
            logger.error(f"✗ 提取字幕失败: {e}")
            return False
    
    
    def extract_with_ocr(self, video_path, output_path=None, method='easyocr', 
                        interval=1.0, lang='ch_sim+en'):
        """
        使用OCR识别视频画面中的文字（硬字幕）
        
        Args:
            video_path: 视频文件路径
            output_path: 输出文件路径（可选）
            method: OCR方法 ('easyocr', 'paddleocr', 'tesseract')
            interval: 采样间隔（秒）
            lang: 语言代码
        """
        video_path = Path(video_path)
        if not video_path.exists():
            logger.error(f"✗ 错误: 文件不存在: {video_path}")
            return False
        
        logger.info(f"使用 {method.upper()} OCR识别视频文字...")
        logger.info("这可能需要几分钟时间，请耐心等待...")
        
        # 检查OCR库
        if method == 'easyocr':
            try:
                import easyocr
                logger.info("✓ EasyOCR 已安装")
            except ImportError:
                logger.error("✗ 未安装 EasyOCR")
                logger.error("  请运行: pip install easyocr")
                return False
        elif method == 'paddleocr':
            try:
                from paddleocr import PaddleOCR
                logger.info("✓ PaddleOCR 已安装")
            except ImportError:
                logger.error("✗ 未安装 PaddleOCR")
                logger.error("  请运行: pip install paddleocr")
                return False
        elif method == 'tesseract':
            try:
                import pytesseract
                from PIL import Image
                logger.info("✓ Tesseract OCR 已安装")
            except ImportError:
                logger.error("✗ 未安装 pytesseract 或 Pillow")
                logger.error("  请运行: pip install pytesseract pillow")
                logger.error("  并安装 Tesseract: https://github.com/tesseract-ocr/tesseract")
                return False
        
        # 提取视频帧
        frames_dir = self.temp_dir / "frames"
        frames_dir.mkdir(exist_ok=True)
        
        logger.info(f"提取视频帧（间隔 {interval} 秒）...")
        cmd = [
            'ffmpeg', '-i', str(video_path),
            '-vf', f'fps=1/{interval}',
            '-q:v', '2',
            str(frames_dir / 'frame_%06d.jpg')
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        
        frame_files = sorted(frames_dir.glob('frame_*.jpg'))
        logger.info(f"✓ 提取了 {len(frame_files)} 帧")
        
        # OCR识别
        results = []
        if method == 'easyocr':
            # 优化：优先使用中文和英文，gpu根据系统自动选择
            try:
                reader = easyocr.Reader(['ch_sim', 'en'], gpu=False, verbose=False)
            except:
                # 如果ch_sim失败，尝试ch_tra
                reader = easyocr.Reader(['ch_tra', 'en'], gpu=False, verbose=False)
            
            for i, frame_file in enumerate(frame_files):
                if (i + 1) % 10 == 0 or i == len(frame_files) - 1:
                    logger.info(f"识别中... {i+1}/{len(frame_files)}")
                result = reader.readtext(
                    str(frame_file),
                    paragraph=False,  # 不自动合并段落
                    detail=1  # 返回详细信息
                )
                timestamp = i * interval
                for detection in result:
                    text = detection[1]
                    confidence = detection[2]
                    # 提高置信度阈值，过滤低质量结果
                    if confidence > 0.6:  # 从0.5提高到0.6
                        # 清理文本
                        text = text.strip()
                        if text:  # 确保文本不为空
                            results.append({
                                'time': timestamp,
                                'text': text,
                                'confidence': confidence
                            })
        
        elif method == 'paddleocr':
            # PaddleOCR 对中文支持更好，优化参数
            ocr = PaddleOCR(
                use_angle_cls=True, 
                lang='ch',  # 中文
                use_gpu=False,
                show_log=False  # 减少日志输出
            )
            for i, frame_file in enumerate(frame_files):
                if (i + 1) % 10 == 0 or i == len(frame_files) - 1:
                    logger.info(f"识别中... {i+1}/{len(frame_files)}")
                result = ocr.ocr(str(frame_file), cls=True)
                timestamp = i * interval
                if result and result[0]:
                    for line in result[0]:
                        if line:
                            text = line[1][0]
                            confidence = line[1][1]
                            # 提高置信度阈值
                            if confidence > 0.6:  # 从0.5提高到0.6
                                text = text.strip()
                                if text:
                                    results.append({
                                        'time': timestamp,
                                        'text': text,
                                        'confidence': confidence
                                    })
        
        elif method == 'tesseract':
            import pytesseract
            from PIL import Image
            for i, frame_file in enumerate(frame_files):
                if (i + 1) % 10 == 0 or i == len(frame_files) - 1:
                    logger.info(f"识别中... {i+1}/{len(frame_files)}")
                img = Image.open(frame_file)
                text = pytesseract.image_to_string(img, lang=lang)
                timestamp = i * interval
                if text.strip():
                    results.append({
                        'time': timestamp,
                        'text': text.strip(),
                        'confidence': 1.0
                    })
        
        logger.info("✓ OCR识别完成")
        
        # 保存结果
        if output_path is None:
            output_path = video_path.parent / f"{video_path.stem}_ocr.txt"
        else:
            output_path = Path(output_path)
        
        # 后处理：去重和合并相似时间戳的文本
        processed_results = []
        if results:
            # 按时间排序
            results.sort(key=lambda x: x['time'])
            
            # 合并相近时间戳的文本（避免重复）
            last_time = -1
            last_text = ""
            merge_threshold = 0.5  # 0.5秒内的文本合并
            
            for item in results:
                if item['time'] - last_time < merge_threshold and last_text:
                    # 合并文本（去重）
                    if item['text'] not in last_text:
                        last_text += " " + item['text']
                else:
                    if last_text:
                        processed_results.append({
                            'time': last_time,
                            'text': last_text.strip()
                        })
                    last_time = item['time']
                    last_text = item['text']
            
            # 添加最后一个
            if last_text:
                processed_results.append({
                    'time': last_time,
                    'text': last_text.strip()
                })
        
        # 保存为文本文件
        with open(output_path, 'w', encoding='utf-8') as f:
            for item in processed_results:
                time_str = self._format_timestamp(item['time'])
                f.write(f"[{time_str}] {item['text']}\n")
        
        logger.info(f"✓ 结果已保存到: {output_path}")
        
        # 清理临时文件
        import shutil
        shutil.rmtree(frames_dir)
        
        return True
    
    def extract_with_asr(self, video_path, output_path=None, method='whisper'):
        """
        使用语音识别提取视频中的文字（ASR）
        
        Args:
            video_path: 视频文件路径
            output_path: 输出文件路径（可选）
            method: ASR方法 ('whisper', 'vosk')
        """
        video_path = Path(video_path)
        if not video_path.exists():
            logger.error(f"✗ 错误: 文件不存在: {video_path}")
            return False
        
        logger.info(f"使用 {method.upper()} 语音识别提取文字...")
        logger.info("这可能需要几分钟时间，请耐心等待...")
        
        # 提取音频 - 提高采样率以获得更好的音质
        audio_path = self.temp_dir / f"{video_path.stem}.wav"
        logger.info("提取音频...")
        cmd = [
            'ffmpeg', '-i', str(video_path),
            '-vn', '-acodec', 'pcm_s16le',
            '-ar', '44100', '-ac', '1',  # 提高采样率到44100Hz，提高音质
            '-y', str(audio_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info("✓ 音频已提取")
        
        if method == 'whisper':
            try:
                import whisper
                logger.info("✓ Whisper 已安装")
            except ImportError:
                logger.error("✗ 未安装 Whisper")
                logger.error("  请运行: pip install openai-whisper")
                return False
            
            logger.info("正在识别语音...")
            # 使用 small 模型，在准确性和速度之间取得平衡
            # 如果需要更高准确性，可以使用 "medium" 或 "large"，但会更慢
            model = whisper.load_model("small")
            
            # 优化 Whisper 参数以提高中文识别准确性
            result = model.transcribe(
                str(audio_path),
                language="zh",  # 明确指定中文
                task="transcribe",  # 转录任务
                temperature=0.0,  # 降低随机性，提高准确性
                beam_size=5,  # 增加beam size提高准确性
                best_of=5,  # 多次采样选择最佳结果
                patience=1.0,  # 耐心参数，提高长文本准确性
                condition_on_previous_text=True,  # 使用上下文信息
                initial_prompt="以下是普通话的语音转录。",  # 中文提示词
                word_timestamps=True,  # 启用词级时间戳
                fp16=False  # 使用FP32提高准确性（如果GPU内存足够）
            )
            
            # 保存结果
            if output_path is None:
                output_path = video_path.parent / f"{video_path.stem}_asr.txt"
            else:
                output_path = Path(output_path)
            
            # 后处理：清理和优化文本
            text = result['text'].strip()
            # 移除多余的空格和换行
            text = ' '.join(text.split())
            # 移除常见的识别错误（可选）
            # text = text.replace(' ', '')  # 中文通常不需要空格
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)
            
            # 保存带时间戳的SRT格式
            srt_path = video_path.parent / f"{video_path.stem}_asr.srt"
            self._save_as_srt(result['segments'], srt_path)
            
            logger.info(f"✓ 结果已保存到: {output_path}")
            logger.info(f"✓ SRT字幕已保存到: {srt_path}")
            return True
        
        elif method == 'vosk':
            try:
                import vosk
                import json
                logger.info("✓ Vosk 已安装")
            except ImportError:
                logger.error("✗ 未安装 Vosk")
                logger.error("  请运行: pip install vosk")
                return False
            
            # Vosk需要下载模型
            logger.warning("✗ Vosk需要下载语言模型，建议使用Whisper")
            return False
        
        return False
    
    def _format_timestamp(self, seconds):
        """格式化时间戳"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def _save_as_srt(self, segments, output_path):
        """保存为SRT字幕格式"""
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(segments, 1):
                start = self._format_timestamp(segment['start'])
                end = self._format_timestamp(segment['end'])
                text = segment['text'].strip()
                f.write(f"{i}\n{start} --> {end}\n{text}\n\n")


def main():
    parser = argparse.ArgumentParser(
        description='从视频中提取文字',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 提取嵌入字幕（软字幕）
  python extract_video_text.py video.mp4 --method subtitle
  
  # 使用OCR识别画面文字（硬字幕）
  python extract_video_text.py video.mp4 --method ocr --ocr-method easyocr
  
  # 使用语音识别提取文字
  python extract_video_text.py video.mp4 --method asr --asr-method whisper
  
  # 列出所有字幕流
  python extract_video_text.py video.mp4 --list-streams
        """
    )
    
    parser.add_argument('video', help='输入视频文件路径')
    parser.add_argument('-o', '--output', help='输出文件路径（可选）')
    parser.add_argument('-m', '--method', 
                       choices=['subtitle', 'ocr', 'asr'],
                       default='subtitle',
                       help='提取方法: subtitle(嵌入字幕), ocr(画面文字), asr(语音识别)')
    parser.add_argument('--ocr-method',
                       choices=['easyocr', 'paddleocr', 'tesseract'],
                       default='easyocr',
                       help='OCR方法 (默认: easyocr)')
    parser.add_argument('--asr-method',
                       choices=['whisper', 'vosk'],
                       default='whisper',
                       help='ASR方法 (默认: whisper)')
    parser.add_argument('--ocr-interval', type=float, default=1.0,
                       help='OCR采样间隔（秒，默认: 1.0）')
    parser.add_argument('--ocr-lang', default='ch_sim+en',
                       help='OCR语言代码 (默认: ch_sim+en)')
    args = parser.parse_args()
    
    extractor = VideoTextExtractor()
    
    if not extractor.check_dependencies():
        sys.exit(1)
    
    success = False
    if args.method == 'subtitle':
        success = extractor.extract_embedded_subtitles(args.video, args.output)
    elif args.method == 'ocr':
        success = extractor.extract_with_ocr(
            args.video, args.output, 
            method=args.ocr_method,
            interval=args.ocr_interval,
            lang=args.ocr_lang
        )
    elif args.method == 'asr':
        success = extractor.extract_with_asr(
            args.video, args.output,
            method=args.asr_method
        )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()


