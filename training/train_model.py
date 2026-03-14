# ------------------------------------------------------------
# Import required libraries
# ------------------------------------------------------------

# Import pandas
# Used to load and manipulate the dataset
import pandas as pd

# Import train_test_split
# Used to divide dataset into training and testing portions
from sklearn.model_selection import train_test_split

# Import XGBoost regression model
# This will learn the mapping between speech features and fluency score
from xgboost import XGBRegressor

# Import pickle
# Used to save the trained model to disk
import pickle


# ------------------------------------------------------------
# Load the training dataset
# ------------------------------------------------------------

# Read the dataset generated earlier
data = pd.read_csv("training_dataset.csv")


# ------------------------------------------------------------
# Define input features
# ------------------------------------------------------------

# These columns represent speech features extracted from audio
features = [
    "speech_rate",
    "pause_count",
    "filler_count",
    "grammar_errors",
    "lexical_diversity"
]


# ------------------------------------------------------------
# Separate input features and target variable
# ------------------------------------------------------------

# X contains the input features used for training
X = data[features]

# y contains the target variable (fluency score)
y = data["fluency_score"]


# ------------------------------------------------------------
# Split dataset into training and testing sets
# ------------------------------------------------------------

# 80% of data will be used for training
# 20% of data will be used for evaluation
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)


# ------------------------------------------------------------
# Initialize XGBoost model
# ------------------------------------------------------------

# Create the regression model
model = XGBRegressor(

    # Number of decision trees in the ensemble
    n_estimators=300,

    # Maximum depth of each tree
    max_depth=6,

    # Learning rate controls how fast model learns
    learning_rate=0.05,

    # Random seed for reproducibility
    random_state=42
)


# ------------------------------------------------------------
# Train the model
# ------------------------------------------------------------

# Fit the model using training data
model.fit(X_train, y_train)


# ------------------------------------------------------------
# Save trained model
# ------------------------------------------------------------

# Open a file in write-binary mode
with open("models/fluency_model.pkl", "wb") as f:

    # Serialize and save the model
    pickle.dump(model, f)


# ------------------------------------------------------------
# Print confirmation
# ------------------------------------------------------------

print("Fluency model trained and saved successfully.")