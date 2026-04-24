import subprocess
import os

def handler(request):
    try:
        # Run the hello.py script
        result = subprocess.run(
            ['python', 'hello.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=os.path.dirname(__file__)  # api directory
        )
        return {
            'statusCode': 200,
            'body': result.stdout
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': str(e)
        }