# TooGoodNotify 

<p align="center">
  <img src="https://github.com/pownedjojo/TooGoodNotify/assets/2340374/f62f2f94-957d-4279-8c77-3214b687299b" alt="MarineGEO circle logo" style="height: 150px; width:150px;"/>
</p>

## 📌 Overview

**TooGoodNotify** is a customizable notification bot for TooGoodToGo (TGTG) deals, designed to monitor TGTG magic bags and notify users via Telegram. Built with a modular architecture and optimized for efficient event-driven operations, this bot is ready for seamless deployment on AWS Lambda.

## 🚀 Features

- 🔄 **Automated Monitoring:** Tracks TGTG magic bags on a set schedule and sends timely notifications.
- 💬 **Telegram Integration:** Allows users to interact with the bot through Telegram commands.
- 🌍 **Multi-language Support:** Available in English and French.
- ☁️ **AWS Lambda Compatible::** Efficient, serverless deployment.


## 🛠️ Installation

1. **Clone the Repository**:
  ```sh
  git clone https://github.com/jordantete/TooGoodNotify.git
  cd TooGoodNotify
  ```

2. **Set Up Conda Environment**:
  ```sh
  conda env create -f environment.yml
  conda activate too_good_notify_env
  ```

3. **Configure Environment Variables in Conda**:

To set multiple environment variables at once, use a `.env` file. This is faster and keeps your configuration organized.

At the root of the project, create a `.env` file and add the necessary environment variables:

  ```plaintext
  # .env
  USER_EMAIL=your_user_email@example.com
  TELEGRAM_BOT_TOKEN=your_telegram_bot_token
  TELEGRAM_CHAT_ID=your_telegram_chat_id
  ACCESS_TOKEN=your_tgtg_access_token
  REFRESH_TOKEN=your_tgtg_refresh_token
  USER_ID=your_tgtg_user_id
  TGTG_COOKIE=your_tgtg_cookie
  USER_AWS_ACCOUNT_ID=your_aws_user_account_id
  LAMBDA_MONITORING_ARN=lambda_arn
  ```

4. **Creating the Lambda Layer**:

To create the Lambda layer, use the following commands:

  ```sh
  cd lambda_layer
  mkdir -p python
  pip install \
      --platform manylinux2014_x86_64 \
      --target=python \
      --implementation cp \
      --python-version 3.10 \
      --only-binary=:all: \
      -r requirements_layer.txt
  zip -r lambda_layer.zip python/
  aws lambda publish-layer-version --layer-name TooGoodNotifyLayer --description "Layer for dependencies" --zip-file fileb://lambda_layer.zip --compatible-runtimes python3.10
  ```

## 🤝 Contributing

Contributions are welcome! If you have ideas, improvements, or bug fixes, feel free to submit an issue or a pull request. Please ensure that your contributions follow the project’s coding standards and include clear descriptions for any changes.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE.txt) file for more details.

## 👀 Feedback

Have any questions or feedback? Feel free to reach out via the issues tab on GitHub. We’d love to hear from you!

## ❗ Disclaimer

**TooGoodNotify** is an independent project and is not affiliated with, endorsed by, or officially connected to TooGoodToGo (TGTG) or any of its subsidiaries or affiliates. All product names, logos, and brands are property of their respective owners.