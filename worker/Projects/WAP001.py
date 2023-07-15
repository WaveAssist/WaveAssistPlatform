def WAN_001():
    print("hello1")
    for i in range(0,10):
        print("It works!!!!!!")

def WAN_002():
    print("hello2")

def WAN_006(WAP1IN1, WAP1IN2, ):
    import pandas as pd
    
    print(WAP1IN1)
    print(WAP1IN2)
    
    df2 = pd.DataFrame({"row2": ["column2"]})
    
    # Create sample data for the classroom
    data = {
        'Name': ['Alice', 'Bob', 'Charlie', 'David'],
        'Age': [20, 21, 19, 20],
        'Gender': ['Female', 'Male', 'Male', 'Male'],
        'Grade': [10, 11, 10, 11]
    }
    
    # Create the DataFrame
    df = pd.DataFrame(data)
    
    # Display the DataFrame
    print(df)
    
    return df, df2
    

