import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
from datetime import datetime
import json
import re
from ratelimit import limits, sleep_and_retry
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app_logs.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configure page
st.set_page_config(
    page_title="Test Kit Analyzer",
    page_icon="🧪",
    layout="wide"
)

# Initialize session state
if 'ammonia_predictions' not in st.session_state:
    st.session_state.ammonia_predictions = []
if 'nitrite_predictions' not in st.session_state:
    st.session_state.nitrite_predictions = []
if 'ph_predictions' not in st.session_state:
    st.session_state.ph_predictions = []

def setup_gemini(api_key):
    """Setup Gemini API with provided API key"""
    try:
        genai.configure(api_key=api_key)
        logger.info("Gemini API configured successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to configure Gemini API: {str(e)}")
        st.sidebar.error(f"Invalid API key: {str(e)}")
        return False

# Rate limit configuration: 20 requests per minute (60 seconds)
REQUESTS_PER_MINUTE = 20
PERIOD = 60  # seconds

@sleep_and_retry
@limits(calls=REQUESTS_PER_MINUTE, period=PERIOD)
def analyze_with_gemini(image, test_type, unit="mg/L"):
    """Analyze test kit image using Gemini with rate limiting"""
    try:
        logger.info(f"Starting analysis for {test_type} test with unit {unit}")
        # Initialize the model
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Define test-specific prompts
        prompts = {
            'ammonia': {
                'color': 'orange',
                'description': 'Ammonia',
                'ranges': '(0.0, 0.5, 1.0, 3.0, or 5.0)',
                'unit_required': True
            },
            'nitrite': {
                'color': 'pink',
                'description': 'Nitrite',
                'ranges': '(0.0, 0.5, 1.0, 3.0, or 5.0)',
                'unit_required': True
            },
            'ph': {
                'color': 'yellow/green/blue',
                'description': 'pH',
                'ranges': '(6.8, 7.0, 7.2, 7.6, 8.0, 8.5)',
                'unit_required': False
            }
        }
        
        test_info = prompts[test_type]
        
        # Create the prompt
        if test_type == 'ph':
            prompt = f"""
            You are an expert at analyzing test kit results. Please analyze this pH test kit image.

            I can see a test tube with colored liquid and a reference color chart (maybe absent sometimes, but if present please consider). Please:
            
            1. Identify the test tube in the image (it's usually a clear glass or plastic tube with yellow, green, or blue liquid).
            2. Compare the color of the liquid in the test tube to the reference color chart shown in the image. If the reference chart is not provided, note that the pH liquid color generally ranges from yellow (acidic) to green (neutral) to blue (alkaline).
            3. Determine which reference color {test_info['ranges']} best matches the test tube liquid.
            4. Provide a confidence level (0-100%) for your assessment.

            Please respond in the following JSON format:
            {{
                "predicted_level": <number>,
                "confidence": <number 0-100>,
                "explanation": "<brief explanation of what you observed>",
                "tube_description": "<description of the test tube liquid color>",
                "matched_reference": "<description of the matching reference color>"
            }}

            Be very precise in your color matching. Look carefully at the liquid inside the test tube and compare it to each reference color block.
            """
        else:
            prompt = f"""
            You are an expert at analyzing test kit results. Please analyze this {test_info['description'].lower()} test kit image.

            I can see a test tube with colored liquid and a reference color chart (maybe absent sometimes, but if present please consider). Please:

            1. Identify the test tube in the image (it's usually a clear glass tube with {test_info['color']}/clear liquid)
            2. Compare the color of the liquid in the test tube to the reference color chart shown in the image if the reference chart is not provided, note that the {test_info['description'].lower()} liquid has a {test_info['color']} color with different intensities
            3. Determine which reference color {test_info['ranges']} {unit} best matches the test tube liquid
            4. Provide a confidence level (0-100%) for your assessment

            Please respond in the following JSON format:
            {{
                "predicted_level": <number>,
                "confidence": <number 0-100>,
                "explanation": "<brief explanation of what you observed>",
                "tube_description": "<description of the test tube liquid color>",
                "matched_reference": "<description of the matching reference color>"
            }}

            Be very precise in your color matching. Look carefully at the liquid inside the test tube and compare it to each reference color block.
            """
        
        # Generate response
        logger.debug(f"Sending prompt to Gemini API for {test_type} analysis")
        response = model.generate_content([prompt, image])
        logger.info(f"Received response from Gemini API for {test_type} analysis")
        
        # Parse JSON response
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                logger.info(f"Successfully parsed JSON response for {test_type}: {result['predicted_level']}")
                return result
            else:
                logger.warning(f"No JSON found in response for {test_type}, falling back to text parsing")
                return parse_text_response(response.text, test_type)
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed for {test_type}: {str(e)}")
            return parse_text_response(response.text, test_type)
            
    except Exception as e:
        logger.error(f"Error analyzing image for {test_type}: {str(e)}")
        st.error(f"Error analyzing image: {str(e)}")
        return None

def parse_text_response(text, test_type):
    """Parse text response if JSON parsing fails"""
    try:
        # Extract numerical values using regex
        level_match = re.search(r'(?:level|prediction).*?(\d+\.?\d*)', text, re.IGNORECASE)
        confidence_match = re.search(r'confidence.*?(\d+)', text, re.IGNORECASE)
        
        predicted_level = float(level_match.group(1)) if level_match else 1.0
        confidence = float(confidence_match.group(1)) if confidence_match else 50.0
        
        result = {
            "predicted_level": predicted_level,
            "confidence": confidence,
            "explanation": text[:200] + "..." if len(text) > 200 else text,
            "tube_description": f"{test_type.capitalize()} analysis completed",
            "matched_reference": f"Closest match: {predicted_level} mg/L"
        }
        logger.info(f"Parsed text response for {test_type}: {result['predicted_level']}")
        return result
    except Exception as e:
        logger.error(f"Error parsing text response for {test_type}: {str(e)}")
        return {
            "predicted_level": 1.0,
            "confidence": 50.0,
            "explanation": "Could not parse detailed results",
            "tube_description": "Analysis attempted",
            "matched_reference": "Default result"
        }

def save_prediction(level, confidence, test_type, unit="", explanation="", image_name=""):
    """Save prediction to CSV file with image name"""
    try:
        new_prediction = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'predicted_level': level,
            'confidence': confidence,
            'unit': unit if test_type != 'ph' else 'pH',
            'test_type': test_type,
            'explanation': explanation,
            'image_name': image_name
        }
        
        # Add to session state
        if test_type == 'ammonia':
            st.session_state.ammonia_predictions.append(new_prediction)
        elif test_type == 'nitrite':
            st.session_state.nitrite_predictions.append(new_prediction)
        else:  # pH
            st.session_state.ph_predictions.append(new_prediction)
        
        # Save to CSV
        all_predictions = (st.session_state.ammonia_predictions + 
                          st.session_state.nitrite_predictions +
                          st.session_state.ph_predictions)
        df = pd.DataFrame(all_predictions)
        df.to_csv('test_predictions.csv', index=False)
        logger.info(f"Saved prediction for {test_type}: {level} {unit if test_type != 'ph' else 'pH'} (image: {image_name})")
    except Exception as e:
        logger.error(f"Error saving prediction for {test_type}: {str(e)}")

def main():
    st.title("Test Kit Analyzer 🧪")
    st.markdown("Upload your test kit image(s) and let AI analyze them instantly!")
    
    # Sidebar for settings
    st.sidebar.header("Settings")
    
    # API Key input
    st.sidebar.subheader("Gemini API Key")
    api_key = st.sidebar.text_input(
        "Enter your Gemini API Key",
        type="password",
        help="""To get a Gemini API key and begin using the Gemini API, follow these steps: \n
                1. **Access Google AI Studio**:\n
                Go to the Google AI Studio webpage.\n
                Sign in with your existing Google account credentials, or create a new account if needed.\n
                2. **Generate API Key**:\n
                On the Google AI Studio page, find and click the "Get API Key" button.\n
                Then, click "Create API Key".\n
                You will be prompted to either select an existing Google Cloud project or create a new one to associate with your API key."""
    )
    
    # Validate API key
    api_key_valid = False
    if api_key:
        api_key_valid = setup_gemini(api_key)
    
    # Unit selection (only for ammonia/nitrite)
    unit = st.sidebar.selectbox(
        "Choose unit (for Ammonia/Nitrite):",
        ["mg/L", "ppm"],
        index=0
    )
    
    # Option to view logs in sidebar
    st.sidebar.subheader("Application Logs")
    if st.sidebar.checkbox("Show Logs"):
        try:
            with open('app_logs.log', 'r') as log_file:
                logs = log_file.read()
                st.sidebar.text_area("Log Output", logs, height=200)
        except FileNotFoundError:
            st.sidebar.info("No logs available yet.")
    
    # Create tabs for different test types
    tab1, tab2, tab3 = st.tabs(["Ammonia Test", "Nitrite Test", "pH Test"])
    
    with tab1:
        st.header("🧪 Ammonia Test Kit Analysis")
        process_test_kit('ammonia', unit, api_key_valid)
        
    with tab2:
        st.header("🧪 Nitrite Test Kit Analysis")
        process_test_kit('nitrite', unit, api_key_valid)
        
    with tab3:
        st.header("🧪 pH Test Kit Analysis")
        process_test_kit('ph', '', api_key_valid)

def process_test_kit(test_type, unit, api_key_valid):
    """Process the test kit analysis for ammonia, nitrite, or pH"""
    test_info = {
        'ammonia': {'name': 'Ammonia', 'unit': unit, 'help': 'Upload one or more images of your ammonia test kit'},
        'nitrite': {'name': 'Nitrite', 'unit': unit, 'help': 'Upload one or more images of your nitrite test kit'},
        'ph': {'name': 'pH', 'unit': '', 'help': 'Upload one or more images of your pH test kit'}
    }
    
    test_name = test_info[test_type]['name']
    
    # File upload with multiple files support
    uploaded_files = st.file_uploader(
        f"Choose {test_name} test kit image(s)...",
        type=['jpg', 'jpeg', 'png'],
        key=f"uploader_{test_type}",
        help=test_info[test_type]['help'],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        logger.info(f"Uploaded {len(uploaded_files)} image(s) for {test_name} test")
        
        # Display all uploaded images
        st.subheader("📷 Uploaded Image(s)")
        cols = st.columns(min(len(uploaded_files), 3))  # Display up to 3 images per row
        for idx, uploaded_file in enumerate(uploaded_files):
            image = Image.open(uploaded_file)
            with cols[idx % 3]:
                st.image(image, caption=f"{uploaded_file.name}", use_container_width=True)
        
        # Single Analyze button for all images
        if st.button(f"🔍 Analyze {test_name} Image(s) with AI", key=f"analyze_{test_type}", type="primary", disabled=not api_key_valid):
            if not api_key_valid:
                st.error("Please enter a valid Gemini API key in the sidebar")
                logger.warning("Attempted analysis without valid API key")
            else:
                st.subheader("🤖 AI Analysis Results")
                results = []
                with st.spinner(f"AI is analyzing your {test_name.lower()} test kit image/s..."):
                    for idx, uploaded_file in enumerate(uploaded_files):
                        image = Image.open(uploaded_file)
                        try:
                            result = analyze_with_gemini(image, test_type, unit)
                            if result:
                                results.append({
                                    'image_name': uploaded_file.name,
                                    'predicted_level': result['predicted_level'],
                                    'confidence': result['confidence'],
                                    'explanation': result.get('explanation', 'No explanation available'),
                                    'tube_description': result.get('tube_description', 'N/A'),
                                    'matched_reference': result.get('matched_reference', 'N/A')
                                })
                                # Save prediction
                                save_prediction(
                                    result['predicted_level'],
                                    result['confidence'],
                                    test_type,
                                    unit if test_type != 'ph' else '',
                                    result.get('explanation', ''),
                                    uploaded_file.name
                                )
                        except Exception as e:
                            logger.error(f"Rate limit or API error for {test_name} image {uploaded_file.name}: {str(e)}")
                            st.error(f"Error analyzing {uploaded_file.name}: {str(e)}. Please wait and try again.")
                
                if results:
                    st.success("✅ AI Analysis Complete!")
                    
                    # Display collective summary
                    st.subheader("📊 Analysis Summary")
                    summary_data = [
                        {
                            'Image Name': r['image_name'],
                            f'{test_name} Level': f"{r['predicted_level']}{' pH' if test_type == 'ph' else f' {unit}'}",
                            'Confidence (%)': f"{r['confidence']:.1f}%"
                        } for r in results
                    ]
                    summary_df = pd.DataFrame(summary_data)
                    st.dataframe(
                        summary_df,
                        column_config={
                            'Image Name': 'Image Name',
                            f'{test_name} Level': f'{test_name} Level',
                            'Confidence (%)': 'Confidence (%)'
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                    
                    # Detailed analysis for each image
                    for idx, result in enumerate(results):
                        with st.expander(f"🔍 Detailed AI Analysis for {result['image_name']}"):
                            st.markdown(f"**Test Tube Description:** {result['tube_description']}")
                            st.markdown(f"**Matched Reference:** {result['matched_reference']}")
                            st.markdown("**Analysis:**")
                            st.write(result['explanation'])
        
        # Prediction history
        st.subheader("📊 Prediction History")
        predictions = (
            st.session_state.ammonia_predictions if test_type == 'ammonia' 
            else st.session_state.nitrite_predictions if test_type == 'nitrite'
            else st.session_state.ph_predictions
        )
        
        if predictions:
            history_df = pd.DataFrame(predictions)
            
            # Format column display based on test type
            if test_type == 'ph':
                column_config = {
                    'timestamp': 'Time',
                    'predicted_level': st.column_config.NumberColumn(
                        'pH Level',
                        format="%.1f"
                    ),
                    'confidence': st.column_config.NumberColumn(
                        'Confidence (%)',
                        format="%.1f%%"
                    ),
                    'unit': None,  # Hide unit column for pH as it's always the same
                    'image_name': 'Image Name'
                }
                display_columns = ['timestamp', 'predicted_level', 'confidence', 'image_name']
            else:
                column_config = {
                    'timestamp': 'Time',
                    'predicted_level': st.column_config.NumberColumn(
                        f'{test_name} Level ({unit})',
                        format="%.1f"
                    ),
                    'confidence': st.column_config.NumberColumn(
                        'Confidence (%)',
                        format="%.1f%%"
                    ),
                    'unit': 'Unit',
                    'image_name': 'Image Name'
                }
                display_columns = ['timestamp', 'predicted_level', 'confidence', 'unit', 'image_name']
            
            st.dataframe(
                history_df[display_columns],
                column_config=column_config,
                hide_index=True,
                use_container_width=True
            )
            
            # Option to download history
            csv = history_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download History as CSV",
                data=csv,
                file_name=f"{test_name.lower()}_test_history.csv",
                mime='text/csv',
                key=f"download_{test_type}"
            )
        else:
            st.info("No previous predictions found.")

if __name__ == "__main__":
    logger.info("Starting Test Kit Analyzer application")
    main()
