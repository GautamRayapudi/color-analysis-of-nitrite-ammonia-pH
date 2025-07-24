# 🧪 Test Kit Analyzer using Gemini AI

The **Test Kit Analyzer** is an AI-powered Streamlit web application that analyzes **Ammonia**, **Nitrite**, and **pH** test kit images using **Google’s Gemini API**. The model detects and compares the color of the liquid inside the test tube with reference color charts to predict chemical levels with confidence.

---

## 🌟 Features

- 📷 Upload one or more images of test kits
- 🔍 Analyze Ammonia, Nitrite, and pH levels using AI
- 💡 Gemini-powered color interpretation and prediction
- 📈 View predictions with confidence scores and explanations
- 🧾 Download prediction history as CSV
- 🪵 Real-time logging and debug visibility
- ⛔ Rate-limited to avoid Gemini API throttling (20 requests/min)

---

## 🗂️ Project Structure

```
test-kit-analyzer/
├── app.py                  # Main Streamlit application
├── requirements.txt        # Python dependencies
├── app.log                 # Runtime logs (generated automatically)
├── test_predictions.csv    # Prediction history (generated)
└── README.md               # This file
```

---

## ⚙️ Setup & Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/test-kit-analyzer.git
   cd test-kit-analyzer
   ```

2. **Create a virtual environment (optional but recommended)**
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Streamlit app**
   ```bash
   streamlit run app.py
   ```

---

## 🔐 How to Get a Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app)
2. Sign in with your Google account
3. Click **“Get API Key”**
4. Choose or create a GCP project
5. Copy the key and paste it into the **Streamlit sidebar input box**

---

## 🧠 How It Works (Approach & Architecture)

1. **User Input:**
   - The user uploads one or more images of test kits (Ammonia, Nitrite, or pH).
   - They choose the test type and optionally select the unit (mg/L or ppm).

2. **Prompt Engineering:**
   - The app sends a detailed prompt to **Gemini 2.0 Flash** to:
     - Identify the test tube
     - Compare liquid color with reference chart
     - Estimate chemical concentration
     - Provide confidence and explanation

3. **Gemini Response Parsing:**
   - The model is expected to return a JSON object.
   - If not, fallback regex-based parsing extracts the prediction and confidence.

4. **Result Handling:**
   - Predictions are shown per image with descriptions and explanations.
   - History is tracked in memory and also saved to `test_predictions.csv`.

5. **Logging:**
   - All actions and errors are logged in `app.log`.
   - Logs can be viewed in the sidebar.

6. **Rate Limiting:**
   - The app uses `ratelimit` to restrict Gemini requests to **20 per minute**.

---

## 📤 Output Files

- **Prediction history:** `test_predictions.csv`
- **Runtime logs:** `app.log`
- **Downloadable CSVs** for each test type

---

## 🔄 Session State Management

Session state is used to:
- Store Ammonia/Nitrite/pH predictions separately
- Retain prediction history across multiple interactions
- Ensure the DataFrame and UI updates without reprocessing

---

## 🧪 Supported Test Ranges

| Test Type | Color Range              | Value Ranges              |
|-----------|--------------------------|---------------------------|
| Ammonia   | Orange shades            | 0.0, 0.5, 1.0, 3.0, 5.0    |
| Nitrite   | Pink shades              | 0.0, 0.5, 1.0, 3.0, 5.0    |
| pH        | Yellow → Green → Blue    | 6.8, 7.0, 7.2, 7.6, 8.0, 8.5|

---

## 🛠️ Future Enhancements

- 🧠 Fine-tune prompt with visual reference embeddings
- 📈 Add time-series visualizations of predictions
- 📦 Docker support for easy deployment
- 📤 Option to email/share results
- 🔍 OCR support to detect labels from reference charts

---

## 🙌 Contributing

We welcome contributions! If you'd like to improve the app, fix bugs, or add new features:
1. Fork the repo
2. Create a new branch (`feature/your-feature-name`)
3. Submit a Pull Request

---

## 📜 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 👨‍🔬 Author

**Gautam Kumar**  
*Data Scientist | AI Engineer*
