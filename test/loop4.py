import time

if __name__ == "__main__":
    
    for i in range(10):
        msg = str(i) + " first lines of my program !!"
        print(msg)
    
    print("Now we will compute stuff very long... please wait...")
    time.sleep(30)
