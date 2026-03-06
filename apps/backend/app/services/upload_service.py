"""
Upload Service - Handle CSV file uploads and ETL processing
Manages: File validation, CSV parsing, data transformation, risk analysis
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging

import pandas as pd
from sqlalchemy.orm import Session

from app.db.models import CustomerDB, LoanApplicationDB, LoanFacilityDB
from app.schemas.schemas import (
    CustomerCreate, 
    LoanApplicationCreate, 
    LoanFacilityCreate
)

logger = logging.getLogger(__name__)

class UploadService:
    """Service to handle file uploads and ETL processing"""
    
    # Configuration
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
    UPLOAD_FOLDER = 'uploads'
    
    # Column mapping for CSV → Credit Risk Model
    COLUMN_MAPPING = {
        'customer_id': ['CustomerKey', 'customer_key', 'id'],
        'customer_name': ['CustomerPONumber', 'customer_name', 'name'],
        'age': ['age'],
        'income': ['SalesAmount', 'income', 'monthly_income'],
        'loan_amount': ['SalesAmount', 'loan_amount', 'amount'],
        'loan_term': ['OrderQuantity', 'loan_term', 'term_months'],
        'interest_rate': ['UnitPrice', 'interest_rate', 'rate'],
        'order_date': ['OrderDateKey', 'order_date', 'application_date'],
        'due_date': ['DueDateKey', 'due_date'],
    }
    
    @staticmethod
    def validate_file(file_path: str) -> Tuple[bool, str]:
        """
        Validate uploaded file
        
        Args:
            file_path: Path to uploaded file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not os.path.exists(file_path):
            return False, "File not found"
        
        # Check file extension
        file_ext = Path(file_path).suffix.lower().lstrip('.')
        if file_ext not in UploadService.ALLOWED_EXTENSIONS:
            return False, f"File type '{file_ext}' not allowed. Allowed: {UploadService.ALLOWED_EXTENSIONS}"
        
        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > UploadService.MAX_FILE_SIZE:
            return False, f"File size ({file_size} bytes) exceeds limit ({UploadService.MAX_FILE_SIZE} bytes)"
        
        if file_size == 0:
            return False, "File is empty"
        
        return True, ""
    
    @staticmethod
    def read_csv(file_path: str, limit_rows: Optional[int] = None) -> pd.DataFrame:
        """
        Read CSV file into DataFrame
        
        Args:
            file_path: Path to CSV file
            limit_rows: Optional row limit for testing
            
        Returns:
            pandas DataFrame
            
        Raises:
            ValueError: If file cannot be read
        """
        try:
            df = pd.read_csv(file_path, nrows=limit_rows)
            logger.info(f"Read CSV file: {file_path}, Rows: {len(df)}, Columns: {len(df.columns)}")
            return df
        except Exception as e:
            logger.error(f"Error reading CSV file: {str(e)}")
            raise ValueError(f"Cannot read CSV file: {str(e)}")
    
    @staticmethod
    def detect_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
        """
        Detect and map columns from DataFrame to Credit Risk model
        
        Args:
            df: pandas DataFrame
            
        Returns:
            Dictionary mapping model fields to DataFrame columns
        """
        detected_columns = {}
        df_columns = df.columns.str.lower().tolist()
        
        for model_field, possible_names in UploadService.COLUMN_MAPPING.items():
            detected_columns[model_field] = None
            
            for possible_name in possible_names:
                if possible_name.lower() in df_columns:
                    detected_columns[model_field] = df.columns[
                        df_columns.index(possible_name.lower())
                    ].item()
                    break
        
        logger.info(f"Detected columns: {detected_columns}")
        return detected_columns
    
    @staticmethod
    def parse_date(date_value) -> Optional[datetime]:
        """
        Parse various date formats
        
        Args:
            date_value: Date value (string, int, or datetime)
            
        Returns:
            datetime object or None
        """
        if pd.isna(date_value):
            return None
        
        # If integer (DateKey format: YYYYMMDD)
        if isinstance(date_value, int):
            try:
                date_str = str(int(date_value)).zfill(8)
                return datetime.strptime(date_str, '%Y%m%d')
            except:
                return None
        
        # Try parsing string
        if isinstance(date_value, str):
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y%m%d']:
                try:
                    return datetime.strptime(date_value.strip(), fmt)
                except:
                    continue
        
        return None
    
    @staticmethod
    def transform_data(
        df: pd.DataFrame,
        column_mapping: Dict[str, Optional[str]]
    ) -> List[Dict]:
        """
        Transform DataFrame to Credit Risk model format
        
        Args:
            df: Source DataFrame
            column_mapping: Column mapping dictionary
            
        Returns:
            List of transformed records
        """
        transformed_records = []
        
        for idx, row in df.iterrows():
            try:
                record = {
                    'customer_id': int(row[column_mapping['customer_id']]) if column_mapping['customer_id'] else idx,
                    'customer_name': str(row[column_mapping['customer_name']]) if column_mapping['customer_name'] else f"Customer_{idx}",
                    'age': int(row[column_mapping['age']]) if column_mapping['age'] and pd.notna(row[column_mapping['age']]) else 25,
                    'income': float(row[column_mapping['income']]) if column_mapping['income'] and pd.notna(row[column_mapping['income']]) else 0,
                    'loan_amount': float(row[column_mapping['loan_amount']]) if column_mapping['loan_amount'] and pd.notna(row[column_mapping['loan_amount']]) else 0,
                    'loan_term': int(row[column_mapping['loan_term']]) if column_mapping['loan_term'] and pd.notna(row[column_mapping['loan_term']]) else 24,
                    'interest_rate': float(row[column_mapping['interest_rate']]) if column_mapping['interest_rate'] and pd.notna(row[column_mapping['interest_rate']]) else 8.5,
                    'order_date': UploadService.parse_date(row[column_mapping['order_date']]) if column_mapping['order_date'] else datetime.now(),
                }
                
                # Validate ranges
                if 18 <= record['age'] <= 150 and record['income'] >= 0 and record['loan_amount'] > 0:
                    transformed_records.append(record)
                    
            except Exception as e:
                logger.warning(f"Error transforming row {idx}: {str(e)}")
                continue
        
        logger.info(f"Transformed {len(transformed_records)} valid records")
        return transformed_records
    
    @staticmethod
    def load_to_database(
        db: Session,
        transformed_records: List[Dict],
        batch_size: int = 100
    ) -> Dict[str, int]:
        """
        Load transformed records to database
        
        Args:
            db: SQLAlchemy Session
            transformed_records: List of transformed records
            batch_size: Batch insert size
            
        Returns:
            Dictionary with counts: {customers: int, applications: int, facilities: int}
        """
        counts = {'customers': 0, 'applications': 0, 'facilities': 0}
        
        try:
            # Process in batches
            for batch_idx in range(0, len(transformed_records), batch_size):
                batch = transformed_records[batch_idx:batch_idx + batch_size]
                
                for record in batch:
                    # 1. Create or update Customer
                    customer = db.query(Customer).filter_by(
                        full_name=record['customer_name']
                    ).first()
                    
                    if not customer:
                        customer = Customer(
                            user_id=4,  # Default to Customer role
                            full_name=record['customer_name'],
                            age=record['age'],
                            monthly_income=record['income'],
                            credit_score=550 + int(record['age'] * 2),  # Simple calculation
                            employment_status='Employed',
                            created_at=datetime.now()
                        )
                        db.add(customer)
                        db.flush()
                        counts['customers'] += 1
                    
                    # 2. Create Loan Application
                    application = LoanApplication(
                        customer_id=customer.customer_id,
                        loan_amount=record['loan_amount'],
                        loan_term=record['loan_term'],
                        interest_rate=record['interest_rate'],
                        loan_status='approved',
                        loan_purpose='Uploaded from CSV',
                        created_at=datetime.now()
                    )
                    db.add(application)
                    db.flush()
                    counts['applications'] += 1
                    
                    # 3. Create Loan Facility
                    facility = LoanFacility(
                        application_id=application.application_id,
                        customer_id=customer.customer_id,
                        facility_type='Term Loan' if record['loan_term'] <= 36 else 'Revolving',
                        approved_amount=record['loan_amount'],
                        interest_rate=record['interest_rate'],
                        start_date=record['order_date'],
                        end_date=datetime.fromordinal(
                            record['order_date'].toordinal() + 
                            (record['loan_term'] * 30)  # Approximate
                        ),
                        status='active',
                        created_at=datetime.now()
                    )
                    db.add(facility)
                    db.flush()
                    counts['facilities'] += 1
                
                # Commit batch
                db.commit()
                logger.info(f"Batch {batch_idx // batch_size + 1} committed: {len(batch)} records")
            
            return counts
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error loading to database: {str(e)}")
            raise
    
    @staticmethod
    async def process_upload(
        db: Session,
        file_path: str,
        limit_rows: Optional[int] = None
    ) -> Dict:
        """
        Main ETL process: Validate → Read → Detect → Transform → Load
        
        Args:
            db: SQLAlchemy Session
            file_path: Path to uploaded file
            limit_rows: Optional row limit for testing
            
        Returns:
            Dictionary with processing results
        """
        result = {
            'success': False,
            'message': '',
            'file_path': file_path,
            'rows_processed': 0,
            'counts': {'customers': 0, 'applications': 0, 'facilities': 0},
            'errors': []
        }
        
        try:
            # Step 1: Validate file
            is_valid, error_msg = UploadService.validate_file(file_path)
            if not is_valid:
                result['message'] = error_msg
                return result
            
            # Step 2: Read CSV
            df = UploadService.read_csv(file_path, limit_rows)
            result['rows_processed'] = len(df)
            
            # Step 3: Detect columns
            column_mapping = UploadService.detect_columns(df)
            
            # Step 4: Transform data
            transformed_records = UploadService.transform_data(df, column_mapping)
            
            if not transformed_records:
                result['message'] = 'No valid records found in file'
                result['errors'].append('All rows failed validation')
                return result
            
            # Step 5: Load to database
            counts = UploadService.load_to_database(db, transformed_records)
            
            result['success'] = True
            result['message'] = f'Successfully uploaded and processed {len(transformed_records)} records'
            result['counts'] = counts
            
            logger.info(f"Upload process completed successfully: {result}")
            return result
            
        except Exception as e:
            result['message'] = f'Error processing upload: {str(e)}'
            result['errors'].append(str(e))
            logger.error(f"Upload process failed: {str(e)}")
            return result
