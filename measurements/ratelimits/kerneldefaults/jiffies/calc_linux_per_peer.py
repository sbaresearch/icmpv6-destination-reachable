HZ_Vals=[100,250,1000]
print(HZ_Vals)
for i in range(0,129,1):	
	HZ_Res=[]
	for HZ in HZ_Vals:
		rate=int(1000/HZ)
		msec_to_jiffies=int((1000+(1000/HZ)-1)/(1000/HZ))
		tmo= msec_to_jiffies >> ((128 - i)>>5) 
		HZ_Res.append(str(tmo*rate))
	print(str(i)+","+",".join(HZ_Res))
	

