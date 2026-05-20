#!/usr/bin/env python3
"""
Simple Image Upload Bot for ImgBB
Uploads all images from a specified directory to ImgBB
"""

import os
import json
import base64
import requests
from pathlib import Path
from getpass import getpass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ImgBBUploadBot:
    def __init__(self):
        self.config_file = "imgbb_config.json"
        self.env_file = ".env"
        self.api_key = None
        self.api_url = "https://api.imgbb.com/1/upload"
        
        # Supported image extensions
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        
    def load_config(self):
        """Load API key from config file or environment variable"""
        # Try environment variable first
        self.api_key = os.getenv('IMGBB_API_KEY')
        if self.api_key:
            return True
            
        # Then try config file
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.api_key = config.get('api_key')
                    return self.api_key is not None
            except:
                return False
        return False
    
    def save_config(self):
        """Save API key to config file and .env"""
        # Save to JSON config
        config = {'api_key': self.api_key}
        with open(self.config_file, 'w') as f:
            json.dump(config, f)
        
        # Save to .env file for production
        with open(self.env_file, 'w') as f:
            f.write(f"IMGBB_API_KEY={self.api_key}\n")
        
        # Set proper permissions (important for VPS)
        os.chmod(self.config_file, 0o600)
        os.chmod(self.env_file, 0o600)
        
        print(f"✅ API key saved to {self.config_file} and {self.env_file}")
    
    def get_api_key(self):
        """Ask user for API key (only once)"""
        print("\n🔑 ImgBB API Key Setup")
        print("-" * 40)
        print("Don't have an API key? Get one from: https://api.imgbb.com/")
        print("-" * 40)
        
        while True:
            self.api_key = getpass("Enter your ImgBB API key: ").strip()
            if self.api_key:
                # Verify the API key
                if self.verify_api_key():
                    self.save_config()
                    return True
                else:
                    print("❌ Invalid API key! Please try again.\n")
            else:
                print("❌ API key cannot be empty!\n")
    
    def verify_api_key(self):
        """Verify if the API key is valid by making a test request"""
        test_image = base64.b64encode(b"test").decode('utf-8')
        try:
            response = requests.post(
                self.api_url,
                data={
                    'key': self.api_key,
                    'image': test_image
                },
                timeout=10
            )
            return response.status_code == 200 and 'error' not in response.text.lower()
        except:
            return False
    
    def upload_image(self, image_path):
        """Upload a single image to ImgBB"""
        try:
            # Read and encode image
            with open(image_path, 'rb') as img_file:
                image_data = base64.b64encode(img_file.read()).decode('utf-8')
            
            # Prepare upload data
            payload = {
                'key': self.api_key,
                'image': image_data,
                'name': Path(image_path).stem
            }
            
            # Upload to ImgBB
            response = requests.post(self.api_url, data=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    image_url = result['data']['url']
                    delete_url = result['data'].get('delete_url', 'N/A')
                    return {
                        'success': True,
                        'filename': Path(image_path).name,
                        'url': image_url,
                        'delete_url': delete_url,
                        'size': result['data']['size']
                    }
                else:
                    return {'success': False, 'error': result.get('error', {}).get('message', 'Unknown error')}
            else:
                return {'success': False, 'error': f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def find_images(self, directory="."):
        """Find all images in the specified directory"""
        images = []
        path = Path(directory)
        
        for ext in self.supported_formats:
            images.extend(path.glob(f"*{ext}"))
            images.extend(path.glob(f"*{ext.upper()}"))
        
        return sorted(set(images))
    
    def upload_all_images(self, directory="."):
        """Upload all images in the directory"""
        images = self.find_images(directory)
        
        if not images:
            print(f"\n📁 No supported images found in '{directory}'")
            print(f"Supported formats: {', '.join(self.supported_formats)}")
            return []
        
        print(f"\n📸 Found {len(images)} image(s) in '{directory}'")
        print("-" * 60)
        
        results = []
        for idx, image_path in enumerate(images, 1):
            print(f"\n[{idx}/{len(images)}] Uploading: {image_path.name}")
            result = self.upload_image(str(image_path))
            
            if result['success']:
                print(f"  ✅ Uploaded successfully!")
                print(f"  🔗 URL: {result['url']}")
                print(f"  🗑️  Delete URL: {result['delete_url']}")
                results.append(result)
            else:
                print(f"  ❌ Failed: {result.get('error', 'Unknown error')}")
                results.append(result)
        
        return results
    
    def save_results(self, results, output_file="upload_results.json"):
        """Save upload results to a JSON file"""
        if results:
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\n💾 Results saved to {output_file}")
    
    def print_summary(self, results):
        """Print upload summary"""
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        
        print("\n" + "="*60)
        print("📊 UPLOAD SUMMARY")
        print("="*60)
        print(f"✅ Successful: {len(successful)}")
        print(f"❌ Failed: {len(failed)}")
        
        if successful:
            print("\n🔗 Uploaded URLs:")
            for result in successful:
                print(f"  • {result['filename']}: {result['url']}")
        
        if failed:
            print("\n❌ Failed uploads:")
            for result in failed:
                print(f"  • {result.get('filename', 'Unknown')}: {result.get('error', 'Unknown error')}")
        
        print("="*60)

def main():
    """Main function"""
    print("🤖 IMGBB IMAGE UPLOAD BOT")
    print("="*40)
    
    bot = ImgBBUploadBot()
    
    # Check if API key exists
    if not bot.load_config():
        print("\n⚠️  No API key found!")
        if not bot.get_api_key():
            print("❌ Failed to setup API key. Exiting.")
            return
    
    print(f"\n✅ API key loaded successfully!")
    
    while True:
        print("\n" + "="*40)
        print("📋 MENU")
        print("="*40)
        print("1. Upload images from current directory")
        print("2. Upload images from specific directory")
        print("3. Change API key")
        print("4. Exit")
        
        choice = input("\n👉 Choose an option (1-4): ").strip()
        
        if choice == '1':
            results = bot.upload_all_images(".")
            if results:
                bot.print_summary(results)
                bot.save_results(results)
        
        elif choice == '2':
            directory = input("📁 Enter directory path: ").strip()
            if os.path.exists(directory):
                results = bot.upload_all_images(directory)
                if results:
                    bot.print_summary(results)
                    bot.save_results(results, f"upload_results_{Path(directory).name}.json")
            else:
                print("❌ Directory does not exist!")
        
        elif choice == '3':
            print("\n🔄 Changing API key...")
            if bot.get_api_key():
                print("✅ API key updated successfully!")
            else:
                print("❌ Failed to update API key!")
        
        elif choice == '4':
            print("\n👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice! Please try again.")

if __name__ == "__main__":
    # Install required package if not present
    try:
        import requests
    except ImportError:
        print("📦 Installing required package: requests")
        os.system("pip install requests")
        import requests
    
    main()