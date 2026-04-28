import React from 'react';
import {View, Text, StyleSheet} from 'react-native';
import Button from './Button';

interface ErrorViewProps {
  message?: string;
  onRetry?: () => void;
}

export default function ErrorView({message = 'Something went wrong.', onRetry}: ErrorViewProps) {
  return (
    <View style={styles.container}>
      <Text style={styles.emoji}>⚠️</Text>
      <Text style={styles.message}>{message}</Text>
      {onRetry ? (
        <Button title="Try Again" onPress={onRetry} style={styles.btn} />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32},
  emoji: {fontSize: 40, marginBottom: 16},
  message: {fontSize: 15, color: '#64748b', textAlign: 'center', marginBottom: 24, lineHeight: 22},
  btn: {width: 160},
});
