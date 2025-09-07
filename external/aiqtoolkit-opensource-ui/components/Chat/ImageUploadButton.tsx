import { IconPhoto } from '@tabler/icons-react';
import { useRef, useState } from 'react';

interface ImageUploadButtonProps {
  onImageSelect: (file: File, base64Content: string) => void;
  disabled?: boolean;
  className?: string;
}

export const ImageUploadButton = ({
  onImageSelect,
  disabled = false,
  className = ''
}: ImageUploadButtonProps) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isHovered, setIsHovered] = useState(false);

  const triggerFileUpload = () => {
    if (disabled) return;
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // 验证文件类型
    const [fileType] = file.type.split('/');
    if (fileType !== 'image') {
      alert('只支持图片文件');
      return;
    }

    // 验证文件大小
    if (file.size > 2 * 1024 * 1024) {
      alert('文件大小不能超过2MB');
      return;
    }

    // 读取文件为Base64
    const reader = new FileReader();
    reader.onload = (loadEvent) => {
      const fullBase64String = loadEvent.target?.result as string;
      if (fullBase64String) {
        onImageSelect(file, fullBase64String);
      }
    };
    reader.readAsDataURL(file);

    // 重置input值，允许选择同一文件
    e.target.value = '';
  };

  return (
    <>
      <button
        className={`relative rounded-sm p-1 text-neutral-800 opacity-60 hover:text-[#76b900] dark:bg-opacity-50 dark:text-neutral-100 dark:hover:text-neutral-200 ${className} ${
          disabled ? 'opacity-30 cursor-not-allowed' : 'cursor-pointer'
        }`}
        onClick={triggerFileUpload}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        disabled={disabled}
        title="上传图片"
      >
        <IconPhoto size={18} />
        {isHovered && !disabled && (
          <span className="absolute -top-8 -left-4 bg-black text-white text-xs px-2 py-1 rounded-md whitespace-nowrap">
            上传图片
          </span>
        )}
      </button>
      
      <input
        type="file"
        ref={fileInputRef}
        style={{ display: 'none' }}
        accept="image/*"
        onChange={handleFileChange}
      />
    </>
  );
};
