# import logging
# from app import create_app
# from flask_migrate import upgrade

# # Configure logging
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# app = create_app()

# if __name__ == "__main__":
#     try:
#         with app.app_context():
#             upgrade()
#         logger.info("Database migration completed successfully")
#         app.run(host="0.0.0.0", port=5000, debug=True)
#     except Exception as e:
#         logger.error(f"An error occurred during startup: {str(e)}", exc_info=True)
