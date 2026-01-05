"""
Path: main.py
Main entry point for the Answer Sheet Scanner application.
Initializes database, loads configuration, and starts multiple processes with error handling.
"""

import sys
import logging
from multiprocessing import Process, Event
from config import Config, ConfigurationError
from lib.model import models
from lib.processes import process_a, process_b, process_c
from lib import logger_config

# Setup logger
logger = logger_config.setup_logger(name=__name__, level=logging.INFO)


def initialize_system() -> bool:
    """
    Initialize the system: validate config and create database tables.
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    try:
        # Step 1: Validate configuration
        logger.info("Validating configuration...")
        Config.validate()
        logger.info("✅ Configuration validated successfully")
        
        # Step 2: Display configuration (optional, useful for debugging)
        if not Config.PRODUCTION_MODE:
            Config.display_config()
        
        # Step 3: Create database tables
        logger.info("Initializing database tables...")
        models.create_table()
        logger.info("✅ Database tables initialized")
        
        return True
        
    except ConfigurationError as e:
        logger.error(f"❌ Configuration error: {e}")
        print("\n" + "="*60)
        print("CONFIGURATION ERROR")
        print("="*60)
        print(f"\n{e}\n")
        print("Please check your .env file and ensure all required variables are set.")
        print("See .env.example for reference.\n")
        print("="*60 + "\n")
        return False
        
    except Exception as e:
        logger.error(f"❌ Initialization error: {e}")
        print(f"\n❌ System initialization failed: {e}\n")
        return False


def start_process_with_monitoring(
    target_func, 
    args_dict: dict, 
    process_name: str,
    status_checker: Event
) -> Process:
    """
    Start a process with error monitoring.
    
    Args:
        target_func: The function to run in the process
        args_dict: Arguments dictionary for the process
        process_name: Name of the process for logging
        status_checker: Shared event for process coordination
    
    Returns:
        Process: The started process
    """
    try:
        # Add status_checker to args if not present
        if "status_checker" not in args_dict:
            args_dict["status_checker"] = status_checker
        
        # Create and start process
        process = Process(
            target=target_func,
            kwargs=args_dict,
            name=process_name
        )
        
        process.start()
        logger.info(f"✅ {process_name} started (PID: {process.pid})")
        return process
        
    except Exception as e:
        logger.error(f"❌ Failed to start {process_name}: {e}")
        status_checker.clear()
        raise


def monitor_processes(processes: list, status_checker: Event) -> None:
    """
    Monitor running processes and handle failures.
    
    Args:
        processes: List of running processes
        status_checker: Shared event for process coordination
    """
    try:
        # Wait for all processes to complete
        for process in processes:
            process.join()
            
            # Check exit code
            if process.exitcode != 0:
                logger.error(f"❌ {process.name} exited with code {process.exitcode}")
                status_checker.clear()
            else:
                logger.info(f"✅ {process.name} completed successfully")
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Keyboard interrupt received. Shutting down processes...")
        status_checker.clear()
        
        # Terminate all processes
        for process in processes:
            if process.is_alive():
                logger.warning(f"Terminating {process.name}...")
                process.terminate()
                process.join(timeout=5)
                
                if process.is_alive():
                    logger.error(f"Force killing {process.name}...")
                    process.kill()
        
        logger.info("All processes stopped")
        
    except Exception as e:
        logger.error(f"❌ Process monitoring error: {e}")
        status_checker.clear()


def main():
    """Main application entry point"""
    
    # Step 1: Initialize system
    logger.info("="*60)
    logger.info("ANSWER SHEET SCANNER - STARTING")
    logger.info("="*60)
    
    if not initialize_system():
        logger.error("System initialization failed. Exiting.")
        sys.exit(1)
    
    # Step 2: Create shared status checker
    status_checker = Event()
    status_checker.set()
    
    # Step 3: Get configuration for each process
    process_a_args = Config.get_process_a_args()
    process_b_args = Config.get_process_b_args()
    process_c_args = Config.get_process_c_args()
    
    # Step 4: Add status_checker to all processes
    process_a_args["status_checker"] = status_checker
    process_b_args["status_checker"] = status_checker
    process_c_args["status_checker"] = status_checker
    
    # Step 5: Start all processes
    processes = []
    
    try:
        logger.info("\nStarting processes...")
        
        # Start Process A (User Interaction)
        task_a = start_process_with_monitoring(
            target_func=process_a.process_a,
            args_dict={"process_A_args": process_a_args},
            process_name="Process A - User Interaction",
            status_checker=status_checker
        )
        processes.append(task_a)
        
        # Start Process B (OCR + Scoring + Firebase)
        task_b = start_process_with_monitoring(
            target_func=process_b.process_b,
            args_dict={"process_B_args": process_b_args},
            process_name="Process B - Background Processing",
            status_checker=status_checker
        )
        processes.append(task_b)
        
        # Start Process C (Future: Image Upload to GDrive)
        # Commented out until implementation is ready
        # task_c = start_process_with_monitoring(
        #     target_func=process_c.process_c,
        #     args_dict={"process_C_args": process_c_args},
        #     process_name="Process C - Image Upload",
        #     status_checker=status_checker
        # )
        # processes.append(task_c)
        
        logger.info(f"\n✅ All processes started successfully ({len(processes)} active)")
        logger.info("="*60 + "\n")
        
        # Step 6: Monitor processes
        monitor_processes(processes, status_checker)
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        status_checker.clear()
        
        # Cleanup: terminate all processes
        for process in processes:
            if process.is_alive():
                process.terminate()
        
        sys.exit(1)
    
    finally:
        logger.info("\n" + "="*60)
        logger.info("ANSWER SHEET SCANNER - SHUTDOWN COMPLETE")
        logger.info("="*60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"❌ Unhandled exception: {e}")
        sys.exit(1)