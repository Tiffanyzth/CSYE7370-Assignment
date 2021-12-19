with open("result.csv","w") as w:
    w.write("total_loss,test_loss\n")
    with open("main.log","r") as f:
        for l in f.readlines():
            if("total_loss" in l):
                w.write(l.split("loss:")[1].replace("\n",""))
            if("test_loss" in l):
                w.write(","+l.split("loss:")[1])