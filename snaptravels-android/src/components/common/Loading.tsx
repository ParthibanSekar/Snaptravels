import React from 'react';
import {View, ActivityIndicator, Text, StyleSheet} from 'react-native';

interface LoadingProps {
  message?: string;
  size?: 'small' | 'large';
  fullScreen?: boolean;
}

export default function Loading({message, size = 'large', fullScreen = false}: LoadingProps) {
  if (fullScreen) {
    return (
      <View style={styles.fullScreen}>
        <ActivityIndicator size={size} color="#6366f1" />
        {message ? <Text style={styles.message}>{message}</Text> : null}
      </View>
    );
  }
  return (
    <View style={styles.inline}>
      <ActivityIndicator size={size} color="#6366f1" />
      {message ? <Text style={styles.message}>{message}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  fullScreen: {flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#fff'},
  inline: {padding: 24, alignItems: 'center'},
  message: {marginTop: 12, fontSize: 14, color: '#64748b'},
});
