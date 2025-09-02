"""
Module pour analyser les bottoms en batch avec cache persistant
Version corrigée pour la sérialisation JSON
"""

import pandas as pd
import json
import os
from datetime import datetime
import time
from exact_bottom_finder import ExactBottomFinder

class BatchExactTimeAnalyzer:
    def __init__(self, cache_file='data/exact_times_cache.json'):
        """Initialise l'analyseur avec cache"""
        self.cache_file = cache_file
        self.finder = ExactBottomFinder()
        self.cache = self.load_cache()
        
    def load_cache(self):
        """Charge le cache depuis le fichier"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_cache(self):
        """Sauvegarde le cache"""
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, default=str)  # Convertir automatiquement en string
    
    def get_cache_key(self, timestamp):
        """Génère une clé de cache pour un timestamp"""
        if isinstance(timestamp, pd.Timestamp):
            return timestamp.isoformat()
        return str(timestamp)
    
    def serialize_result(self, result):
        """Convertit un résultat pour qu'il soit sérialisable en JSON"""
        serialized = {}
        for key, value in result.items():
            if isinstance(value, pd.Timestamp):
                serialized[key] = value.isoformat()
            elif isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif pd.isna(value):
                serialized[key] = None
            else:
                serialized[key] = value
        return serialized
    
    def deserialize_result(self, result):
        """Reconvertit un résultat depuis le format JSON"""
        deserialized = {}
        for key, value in result.items():
            if key in ['exact_time', 'original_time', 'timestamp'] and value:
                try:
                    deserialized[key] = pd.Timestamp(value)
                except:
                    deserialized[key] = value
            else:
                deserialized[key] = value
        return deserialized
    
    def analyze_batch(self, bottoms_df, batch_size=20, delay=1.0, progress_callback=None):
        """
        Analyse un batch de bottoms avec gestion du cache
        
        Args:
            bottoms_df: DataFrame avec les bottoms
            batch_size: Taille des batches
            delay: Délai entre requêtes (secondes)
            progress_callback: Fonction callback(processed, total, message)
        
        Returns:
            results_df: DataFrame avec les résultats
            errors: Liste des erreurs
        """
        results = []
        errors = []
        total = len(bottoms_df)
        processed = 0
        
        for idx, row in bottoms_df.iterrows():
            cache_key = self.get_cache_key(idx)
            
            # Vérifier le cache
            if cache_key in self.cache:
                cached_result = self.deserialize_result(self.cache[cache_key])
                results.append(cached_result)
                processed += 1
                if progress_callback:
                    progress_callback(processed, total, f"Chargé depuis cache: {idx}")
                continue
            
            # Analyser le bottom
            try:
                # Passer le prix si disponible
                kwargs = {}
                if 'price' in row:
                    kwargs['price'] = row['price']
                
                result = self.finder.get_exact_bottom_time(
                    bottom_time=idx,
                    **kwargs
                )
                
                if result:
                    # Ajouter le timestamp original
                    result['timestamp'] = idx
                    results.append(result)
                    
                    # Sérialiser et mettre en cache
                    serialized_result = self.serialize_result(result)
                    self.cache[cache_key] = serialized_result
                    
                    # Sauvegarder périodiquement
                    if processed % 10 == 0:
                        self.save_cache()
                else:
                    errors.append({
                        'timestamp': str(idx),
                        'error': 'No data returned'
                    })
                
            except Exception as e:
                errors.append({
                    'timestamp': str(idx),
                    'error': str(e)
                })
            
            processed += 1
            if progress_callback:
                progress_callback(processed, total, f"Analysé: {idx}")
            
            # Pause entre requêtes
            if processed < total:
                time.sleep(delay)
        
        # Sauvegarder le cache final
        self.save_cache()
        
        # Créer DataFrame des résultats
        if results:
            results_df = pd.DataFrame(results)
            return results_df, errors
        
        return pd.DataFrame(), errors
    
    def get_statistics(self):
        """Retourne les statistiques du cache"""
        stats = {
            'total_cached': len(self.cache),
            'cache_size_kb': 0,
            'oldest_entry': None,
            'newest_entry': None
        }
        
        if self.cache:
            # Taille du cache
            cache_str = json.dumps(self.cache, default=str)
            stats['cache_size_kb'] = len(cache_str.encode()) / 1024
            
            # Dates
            timestamps = list(self.cache.keys())
            stats['oldest_entry'] = min(timestamps) if timestamps else None
            stats['newest_entry'] = max(timestamps) if timestamps else None
        
        return stats
    
    def clear_cache(self):
        """Efface le cache"""
        self.cache = {}
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
    
    def export_to_csv(self, filename='data/exact_times_export.csv'):
        """Exporte le cache vers CSV"""
        if self.cache:
            # Désérialiser les résultats pour le CSV
            deserialized_data = {}
            for key, value in self.cache.items():
                deserialized_data[key] = self.deserialize_result(value)
            
            df = pd.DataFrame.from_dict(deserialized_data, orient='index')
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            df.to_csv(filename)
            return filename
        return None