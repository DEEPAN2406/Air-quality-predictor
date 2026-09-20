import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.svm import SVR
from sklearn.metrics import r2_score

print("Loading dataset...")

df = pd.read_csv("dataset/city_day.csv")

features = ['PM2.5','PM10','NO2','SO2','CO','O3']
df = df[features + ['AQI']].dropna()

# 🔽 LIMIT DATA (VERY IMPORTANT)
df = df.sample(10000, random_state=42)   # prevents hanging

X = df[features]
y = df['AQI']

print("Splitting dataset...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print("Training Random Forest...")
rf = RandomForestRegressor(n_estimators=50)
rf.fit(X_train, y_train)

print("Training Decision Tree...")
dt = DecisionTreeRegressor()
dt.fit(X_train, y_train)

print("Training SVM (slow)...")
svm = SVR(kernel='rbf')
svm.fit(X_train, y_train)

print("Models trained successfully ✅")

def get_accuracy():
    return {
        "Random Forest": round(r2_score(y_test, rf.predict(X_test))*100,2),
        "Decision Tree": round(r2_score(y_test, dt.predict(X_test))*100,2),
        "SVM": round(r2_score(y_test, svm.predict(X_test))*100,2)
    }

def predict_aqi(data, algo):
    if algo == "Random Forest":
        return rf.predict([data])[0]
    elif algo == "Decision Tree":
        return dt.predict([data])[0]
    else:
        return svm.predict([data])[0]

def predict_all(data):
    return {
        "Random Forest": rf.predict([data])[0],
        "Decision Tree": dt.predict([data])[0],
        "SVM": svm.predict([data])[0]
    }

def get_best_algorithm(results, accuracy):
    # choose algorithm with highest accuracy
    return max(accuracy, key=accuracy.get)

def get_aqi_category(aqi):
    if aqi <= 50:
        return "Good"
    elif aqi <= 100:
        return "Satisfactory"
    elif aqi <= 200:
        return "Moderate"
    elif aqi <= 300:
        return "Poor"
    elif aqi <= 400:
        return "Very Poor"
    else:
        return "Severe"

def get_aqi_color(aqi):
    if aqi <= 50:
        return "success"   # green
    elif aqi <= 100:
        return "info"
    elif aqi <= 200:
        return "warning"
    elif aqi <= 300:
        return "danger"
    elif aqi <= 400:
        return "dark"
    else:
        return "secondary"

def get_health_advice(aqi):
    if aqi <= 50:
        return "Air quality is good. Enjoy outdoor activities."
    elif aqi <= 100:
        return "Air quality is acceptable. Sensitive individuals should take care."
    elif aqi <= 200:
        return "People with heart or lung diseases should reduce prolonged outdoor exertion."
    elif aqi <= 300:
        return "Everyone may experience breathing discomfort. Avoid outdoor activities."
    elif aqi <= 400:
        return "Serious health effects possible. Stay indoors and wear masks if outside."
    else:
        return "Emergency condition. Avoid all outdoor activities."

def get_dos_donts(aqi):
    if aqi <= 100:
        return (
            ["Enjoy outdoor activities", "Keep windows open"],
            ["No major restrictions"]
        )
    elif aqi <= 200:
        return (
            ["Wear mask if sensitive", "Limit outdoor exercise"],
            ["Avoid long outdoor exposure"]
        )
    else:
        return (
            ["Stay indoors", "Use air purifiers", "Wear N95 mask"],
            ["Avoid outdoor exercise", "Avoid polluted areas"]
        )
